"""各コマの画像を生成する（プロバイダはconfig/style.yamlのgeneration.providerで切替）。

台本のscene + config/style.yaml(絵柄) + config/characters.yaml(キャラ定義)から
プロンプトを組み立て、output/<id>/panels/panel_N.png に保存する。
テキスト・吹き出しは一切描かせない（後工程のembed_text.pyが埋め込む）。

実際の画像生成APIの呼び出しは scripts/providers/<provider>/ に切り出してある
（現状は comfyui: ローカルComfyUI API のみ）。

--mock を付けるとAPIを呼ばずプレースホルダー画像を生成する（レイアウト確認用）。
"""
import argparse
import datetime
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import embed_text  # noqa: E402  (caption_position_for を流用。実際に画像へ重なる領域を計算するため)
import providers  # noqa: E402

# 吹き出し/キャプション枠のプリセット位置 → 空けておいてほしい場所の指示
_SPACE_HINTS = {
    "top": "the top area of the image",
    "top-left": "the upper-left area of the image",
    "top-right": "the upper-right area of the image",
    "bottom": "the bottom area of the image",
    "bottom-left": "the lower-left area of the image",
    "bottom-right": "the lower-right area of the image",
    "center": "the center of the image",
}


def lookup_character(key, script, cfgs):
    """台本の local_characters（記事固有キャラ）を優先し、次に
    config/characters.yaml（複数漫画で使い回すキャノンキャラ）を見る。"""
    local = (script.get("local_characters") or {}).get(key)
    if local:
        return local
    return cfgs["characters"].get(key)


def character_prompt_line(key, char):
    """1キャラぶんの容姿説明行を組み立てる。

    新形式（appearance + default_look、config/characters.yamlの現行キャラが
    この形式）なら、恒常的な容姿と「sceneが上書きしなければこれを着る」という
    既定の服装・表情を分けて明示する——両者の優先関係を1本のdescriptionに混在
    させて長い優先指示文で解決しようとしていた従来のやり方より、モデルへ渡す
    情報自体の構造で曖昧さを減らす狙い。
    旧形式（description一本）はそのまま使う（後方互換。台本のlocal_characters
    の大半が現状この形式のため、character_prompt_line側で両方を吸収する）。
    """
    appearance = char.get("appearance")
    if appearance:
        line = f"{key}: {appearance.strip()}"
        default_look = char.get("default_look")
        if default_look:
            line += (" Default look (use this only if the Scene below does not "
                     f"specify different clothing/expression for this moment): "
                     f"{default_look.strip()}")
        return line
    return f"{key}: {char['description'].strip()}"


def build_prompt(script, panel, cfgs, provider_name=None, panel_idx=None):
    style = cfgs["style"]
    provider_name = provider_name or style["generation"].get("provider", "comfyui")
    prompt_style = style["prompt"][provider_name]
    parts = [prompt_style["style_prompt"].strip()]

    names = panel.get("characters") or []
    descs = []
    for key in names:
        char = lookup_character(key, script, cfgs)
        if not char:
            raise ValueError(
                f"{script['id']}: panel character key '{key}' not found in "
                "local_characters or config/characters.yaml (typo? forgot to "
                "register it?)")
        # キー名を明示的に容姿説明の先頭へ結び付ける。scene側も同じキー名で
        # 人物を呼ぶ運用（CLAUDE.md）なので、モデルに「このキー名 = この容姿」
        # という対応を直接渡し、登場順一致だけに頼らないようにする
        descs.append(character_prompt_line(key, char))
    if descs:
        parts.append("Characters appearing in this image (their default appearance — keep "
                     "face, hair, and build exactly consistent with this at all times). If "
                     "the Scene description below explicitly describes different clothing, "
                     "protective gear, or accessories for this particular moment, the Scene "
                     "always overrides this default clothing — draw what the Scene says they "
                     "are wearing here, not the default outfit listed below:\n- "
                     + "\n- ".join(descs))

    caption_en = (panel.get("caption") or {}).get("en")
    if caption_en:
        # captionは記事文からの引用で、収容規則や一般的性質のように単一の瞬間に
        # 限定されない文も多い。以前は「この文が描写する内容をそのまま描け」と
        # 一律に命じており、単一の瞬間を要求するcomposition_rulesと衝突する
        # ことがあった。captionは「絵が矛盾してはいけない事実の裏付け」、実際に
        # 描く瞬間はsceneが決める、と役割を分けて渡す
        parts.append(
            "Source context (not visible writing) — background facts this image "
            "must stay consistent with, but do not necessarily depict all of at "
            "once: \"" + caption_en.strip() + "\". Depict the single moment "
            "described in the Scene below; that moment should be one instance of "
            "these facts, not a different or unrelated event. Do NOT render this "
            "sentence, or any text, as writing anywhere in the image.")

    parts.append("Scene: " + panel["scene"].strip())

    hints = []
    # 現行の台本はbubblesを使わずcaptionのみで運用しているが、そのcaption枠
    # （config/layout.yamlのcaption_presets）が実際に絵へ重なる。以前はbubbles
    # 分の余白指示しか生成プロンプトに渡しておらず、captionが使われる現行運用
    # では実質死んでいたため、caption位置についても同様に余白を確保するよう伝える
    if panel_idx is not None and panel.get("caption"):
        caption_pos = embed_text.caption_position_for(
            panel, panel_idx, cfgs["layout"].get("caption", {}))
        if isinstance(caption_pos, str) and caption_pos in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[caption_pos])
    for bubble in panel.get("bubbles") or []:
        pos = bubble.get("position", "top")
        if isinstance(pos, str) and pos in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[pos])
    if hints:
        parts.append("Leave calm, uncluttered empty space (plain background) in "
                     + " and ".join(dict.fromkeys(hints))
                     + " so a caption or speech-bubble box can be overlaid there "
                       "later — keep faces, hands, and essential props outside that area.")

    parts.append(prompt_style["composition_rules"].strip())
    parts.append(prompt_style["no_text_rules"].strip())
    return "\n\n".join(parts)


def collect_reference_images(script, panel, cfgs, prev_panel_paths):
    """キャラクター参照画像 + 直前コマ画像をPIL Imageで返す。"""
    gen = cfgs["style"]["generation"]
    refs = []
    for key in panel.get("characters") or []:
        char = lookup_character(key, script, cfgs) or {}
        for rel in char.get("reference_images") or []:
            path = cfglib.rootpath(rel)
            if os.path.exists(path):
                refs.append(Image.open(path))
    if gen.get("use_previous_panels_as_reference") and prev_panel_paths:
        for path in prev_panel_paths[-2:]:  # 直前2コマまで
            refs.append(Image.open(path))
    return refs[: gen.get("max_reference_images", 6)]


def make_mock_panel(index):
    img = Image.new("RGB", (1024, 1024), (225, 225, 228))
    d = ImageDraw.Draw(img)
    d.rectangle((20, 20, 1004, 1004), outline=(120, 120, 130), width=6)
    d.ellipse((362, 462, 662, 762), outline=(120, 120, 130), width=8)
    d.text((472, 180), f"PANEL {index}", fill=(90, 90, 100), font_size=60)
    return img


def _check_panel_index(script, panel):
    n = len(script["panels"])
    if panel is not None and not (1 <= panel <= n):
        raise ValueError(f"--panel must be between 1 and {n} (got {panel})")


def _merge_prompts_log(existing, new_entries):
    """panel番号をキーに、既存ログへ新しいエントリを上書きマージする
    （--panel指定で1コマだけ再生成した場合に他コマのログを消さないため）。"""
    by_panel = {e["panel"]: e for e in existing}
    for e in new_entries:
        by_panel[e["panel"]] = e
    return [by_panel[k] for k in sorted(by_panel)]


def generate(script, cfgs, mock=False, panel=None):
    """全コマ、または panel（1始まりのコマ番号）を指定すればそのコマだけ生成する。"""
    _check_panel_index(script, panel)
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(panels_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    provider_name = gen_cfg.get("provider", "comfyui")
    provider = providers.get(provider_name) if not mock else None

    n = len(script["panels"])
    targets = [panel] if panel else list(range(1, n + 1))

    # 単一コマ指定時、前コマ参照用にディスク上の既存panel_k.pngを拾っておく
    prev_paths = []
    for k in range(1, targets[0]):
        existing = os.path.join(panels_dir, f"panel_{k}.png")
        if os.path.exists(existing):
            prev_paths.append(existing)

    prompts_log = []
    for i in targets:
        p = script["panels"][i - 1]
        out_path = os.path.join(panels_dir, f"panel_{i}.png")
        prompt = build_prompt(script, p, cfgs, provider_name, panel_idx=i - 1)
        prompts_log.append({"panel": i, "prompt": prompt})
        print(f"[generate] panel {i}/{n}")
        if mock:
            img = make_mock_panel(i)
        else:
            refs = collect_reference_images(script, p, cfgs, prev_paths)
            img, _seed = provider.generate_image(prompt, refs, gen_cfg)
        img.convert("RGB").save(out_path)
        prev_paths.append(out_path)

    prompts_path = os.path.join(panels_dir, "prompts.json")
    existing_log = []
    if os.path.exists(prompts_path):
        with open(prompts_path, encoding="utf-8") as f:
            existing_log = json.load(f)
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(_merge_prompts_log(existing_log, prompts_log), f, ensure_ascii=False, indent=2)
    return comic_dir


def _next_variant_start(temp_dir, panel_index):
    """panel_{panel_index}_vM.pngの既存最大Mを調べ、続きの番号(M+1)を返す。

    既存候補を上書きしないよう、生成のたびに新しいバージョン番号から採番する。
    """
    prefix = f"panel_{panel_index}_v"
    max_v = 0
    if os.path.isdir(temp_dir):
        for name in os.listdir(temp_dir):
            if name.startswith(prefix) and name.endswith(".png"):
                num = name[len(prefix):-len(".png")]
                if num.isdigit():
                    max_v = max(max_v, int(num))
    return max_v + 1


def generate_variants(script, cfgs, count, mock=False, panel=None):
    """各コマにつきcount枚の候補を output/<id>/panels_temp/panel_N_vM.png に生成する。
    panel（1始まりのコマ番号）を指定すればそのコマだけ候補を追加生成する。

    panels/panel_N.png には一切書き込まない（選別前の下書き置き場）。
    人手でpanels_temp/から気に入った1枚を選び、panels/panel_N.pngとして
    保存してから --skip-generate で合成・埋め込みを実行する運用を想定している。
    既に候補が残っている場合は上書きせず、次のバージョン番号から追加生成する。
    """
    _check_panel_index(script, panel)
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    temp_dir = os.path.join(comic_dir, "panels_temp")
    os.makedirs(temp_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    provider_name = gen_cfg.get("provider", "comfyui")
    provider = providers.get(provider_name) if not mock else None

    n = len(script["panels"])
    targets = [panel] if panel else list(range(1, n + 1))

    prompts_log = []
    candidates_path = os.path.join(temp_dir, "candidates.jsonl")
    for i in targets:
        p = script["panels"][i - 1]
        prompt = build_prompt(script, p, cfgs, provider_name, panel_idx=i - 1)
        prompts_log.append({"panel": i, "prompt": prompt})
        start = _next_variant_start(temp_dir, i)
        for offset in range(count):
            v = start + offset
            image_name = f"panel_{i}_v{v}.png"
            out_path = os.path.join(temp_dir, image_name)
            print(f"[generate] panel {i}/{n} variant v{v} ({offset + 1}/{count})")
            seed = None
            if mock:
                img = make_mock_panel(i)
            else:
                # 選別前の下書きなので前コマ参照は使わない（コマ間でまだキャラが
                # 確定していないため）
                img, seed = provider.generate_image(prompt, [], gen_cfg)
            img.convert("RGB").save(out_path)
            # 候補1枚ごとに、それを生成した条件（scene・完成prompt・実seed）を
            # 追記専用のjsonlへ記録する。prompts.json（下記）はパネル番号ごとに
            # 最新のprompt/sceneで上書きしてしまうため、sceneを直してから
            # 再生成すると「この過去の候補v3は、当時どのsceneで生成したものか」が
            # 分からなくなっていた。1行1候補で追記するここでは上書きが起きない
            with open(candidates_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "image": image_name,
                    "panel": i,
                    "scene": p["scene"],
                    "prompt": prompt,
                    "seed": seed,
                    "mock": mock,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, ensure_ascii=False) + "\n")

    # 画像候補(panel_N_vM.png)は上書きせず積み上げるが、prompts.jsonは
    # パネル番号ごとに最新のプロンプトだけ残す（ログの肥大・重複を防ぐ。過去の
    # 候補ごとの生成条件はcandidates.jsonl側で追記保持しているのでここでは
    # 「今どのプロンプトで生成しているか」がひと目で分かれば十分）
    prompts_path = os.path.join(temp_dir, "prompts.json")
    existing_log = []
    if os.path.exists(prompts_path):
        with open(prompts_path, encoding="utf-8") as f:
            existing_log = json.load(f)
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(_merge_prompts_log(existing_log, prompts_log), f, ensure_ascii=False, indent=2)

    panels_rel = os.path.relpath(os.path.join(comic_dir, "panels"), cfglib.ROOT)
    temp_rel = os.path.relpath(temp_dir, cfglib.ROOT)
    print(f"\n[generate] {len(targets)} panel(s) x {count} variants -> {temp_rel}/")
    print(f"気に入った候補を選び {temp_rel}/panel_N_vM.png を {panels_rel}/panel_N.png "
          f"としてコピーしたら、次を実行してください:")
    print(f"  python scripts/run_pipeline.py --id {script['id']} --skip-generate")
    return temp_dir


def export_prompts(script, cfgs):
    """APIを呼ばず、Google AI Studioで手動生成するためのプロンプト・参照画像・
    手順書を output/<id>/prompts/ に書き出す。画像生成そのものは行わない。"""
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    prompts_dir = os.path.join(comic_dir, "prompts")
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(prompts_dir, exist_ok=True)
    os.makedirs(panels_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    provider_name = gen_cfg.get("provider", "comfyui")
    use_prev = gen_cfg.get("use_previous_panels_as_reference")
    panels_rel = os.path.relpath(panels_dir, cfglib.ROOT)

    for i, panel in enumerate(script["panels"], 1):
        prompt = build_prompt(script, panel, cfgs, provider_name, panel_idx=i - 1)

        char_refs = []
        for key in panel.get("characters") or []:
            char = lookup_character(key, script, cfgs) or {}
            for rel in char.get("reference_images") or []:
                src = cfglib.rootpath(rel)
                if os.path.exists(src):
                    char_refs.append((key, src))

        note_lines = []
        if char_refs:
            note_lines.append(f"[添付する参照画像: panel_{i}_refs/ 内の全ファイル]")
        if use_prev and i > 1:
            prev_ids = [p for p in range(max(1, i - 2), i)]
            note_lines.append(
                "[前コマ参照が有効: panel_" + ", panel_".join(str(p) for p in prev_ids)
                + " を生成済みならその画像も参照画像として追加で添付してください]")

        prompt_path = os.path.join(prompts_dir, f"panel_{i}.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt + "\n")
            if note_lines:
                f.write("\n" + "\n".join(note_lines) + "\n")

        if char_refs:
            refs_dir = os.path.join(prompts_dir, f"panel_{i}_refs")
            os.makedirs(refs_dir, exist_ok=True)
            for idx, (key, src) in enumerate(char_refs, 1):
                ext = os.path.splitext(src)[1] or ".png"
                shutil.copyfile(src, os.path.join(refs_dir, f"{idx:02d}_{key}{ext}"))

        print(f"[export] panel {i}/{len(script['panels'])} -> "
              f"{os.path.relpath(prompt_path, cfglib.ROOT)}")

    cfg = gen_cfg.get("comfyui", {})
    readme_lines = [
        f"=== {script['id']} をComfyUIで手動生成する手順 ===",
        "",
        "このプロジェクトは通常 `python scripts/run_pipeline.py --id "
        f"{script['id']}` でComfyUIのAPI ({cfg.get('server', 'http://127.0.0.1:8188')}) "
        "を自動的に叩いて生成する（詳細: scripts/providers/comfyui/README.md）。",
        "APIサーバーを使わずComfyUIのUIで手動生成したい場合:",
        f"1. ComfyUIのUIで scripts/providers/comfyui/workflow_api.json 相当の"
        f"txt2imgワークフロー（チェックポイント: {cfg.get('checkpoint')}）を組む。",
        "2. panel_N.txt の中身をPositive Promptノードに貼り付けて生成する。",
        f"3. 気に入った画像を {panels_rel}/panel_N.png として保存する（Nと採番を一致させること）。",
        "",
        f"全コマ分の画像を {panels_rel}/panel_N.png として保存し終えたら:",
        f"  python scripts/run_pipeline.py --id {script['id']} --skip-generate",
        "を実行すると、合成・15言語分のテキスト埋め込みまで自動で行われる。",
    ]
    readme_path = os.path.join(prompts_dir, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines) + "\n")
    print(f"[export] instructions -> {os.path.relpath(readme_path, cfglib.ROOT)}")
    return prompts_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--export-prompts", action="store_true",
                    help="APIを呼ばずGoogle AI Studio向けにプロンプト・参照画像を書き出す")
    ap.add_argument("--variants", type=int,
                    help="コマごとにN枚の候補をpanels_temp/に生成する（選別用、panels/は書き換えない）")
    ap.add_argument("--panel", type=int,
                    help="指定したコマ番号（1始まり）だけ生成する。省略時は全コマ")
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    if args.export_prompts:
        export_prompts(script, cfgs)
    elif args.variants:
        generate_variants(script, cfgs, args.variants, mock=args.mock, panel=args.panel)
    else:
        generate(script, cfgs, mock=args.mock, panel=args.panel)


if __name__ == "__main__":
    main()
