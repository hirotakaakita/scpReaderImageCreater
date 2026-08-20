"""各コマの画像を生成する（プロバイダはconfig/style.yamlのgeneration.providerで切替）。

台本のscene + config/style.yaml(絵柄) + config/characters.yaml(キャラ定義)から
プロンプトを組み立て、output/<id>/panels/panel_N.png に保存する。
テキスト・吹き出しは一切描かせない（後工程のembed_text.pyが埋め込む）。

実際の画像生成APIの呼び出しは scripts/providers/<provider>/ に切り出してある
（gemini: Nano Banana / comfyui: ローカルComfyUI API）。

--mock を付けるとAPIを呼ばずプレースホルダー画像を生成する（レイアウト確認用）。
"""
import argparse
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import providers  # noqa: E402

# 吹き出しプリセット位置 → 空けておいてほしい場所の指示
_SPACE_HINTS = {
    "top": "the top area of the image",
    "top-left": "the upper-left area of the image",
    "top-right": "the upper-right area of the image",
    "bottom": "the bottom area of the image",
    "bottom-left": "the lower-left area of the image",
    "bottom-right": "the lower-right area of the image",
    "center": "the center of the image",
}


def build_prompt(script, panel, cfgs, provider_name=None):
    style = cfgs["style"]
    characters = cfgs["characters"]
    provider_name = provider_name or style["generation"].get("provider", "gemini")
    prompt_style = style["prompt"][provider_name]
    parts = [prompt_style["style_prompt"].strip()]

    names = panel.get("characters") or []
    descs = []
    for key in names:
        if key in characters:
            descs.append(characters[key]["description"].strip())
    if descs:
        parts.append("Characters appearing in this panel (keep these designs exactly consistent):\n- "
                     + "\n- ".join(descs))

    caption_en = (panel.get("caption") or {}).get("en")
    if caption_en:
        parts.append(
            "This panel illustrates the following in-universe document sentence. "
            "The scene description below must depict exactly what this sentence "
            "describes (same subject, same action/state) — do not draw a different "
            "moment or unrelated action. Do NOT render this sentence, or any text, "
            "as writing anywhere in the image; it is context only:\n"
            f"\"{caption_en.strip()}\"")

    parts.append("Scene: " + panel["scene"].strip())

    hints = []
    for bubble in panel.get("bubbles") or []:
        pos = bubble.get("position", "top")
        if isinstance(pos, str) and pos in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[pos])
    if hints:
        parts.append("Leave calm, uncluttered empty space (plain background) in "
                     + " and ".join(dict.fromkeys(hints))
                     + " so a speech bubble can be overlaid there later.")

    parts.append(prompt_style["composition_rules"].strip())
    parts.append(prompt_style["no_text_rules"].strip())
    return "\n\n".join(parts)


def collect_reference_images(script, panel, cfgs, prev_panel_paths):
    """キャラクター参照画像 + 直前コマ画像をPIL Imageで返す。"""
    gen = cfgs["style"]["generation"]
    refs = []
    for key in panel.get("characters") or []:
        char = cfgs["characters"].get(key) or {}
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


def generate(script, cfgs, mock=False):
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(panels_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    provider_name = gen_cfg.get("provider", "gemini")
    provider = providers.get(provider_name) if not mock else None
    prompts_log = []
    prev_paths = []
    for i, panel in enumerate(script["panels"], 1):
        out_path = os.path.join(panels_dir, f"panel_{i}.png")
        prompt = build_prompt(script, panel, cfgs, provider_name)
        prompts_log.append({"panel": i, "prompt": prompt})
        print(f"[generate] panel {i}/{len(script['panels'])}")
        if mock:
            img = make_mock_panel(i)
        else:
            refs = collect_reference_images(script, panel, cfgs, prev_paths)
            img = provider.generate_image(prompt, refs, gen_cfg)
        img.convert("RGB").save(out_path)
        prev_paths.append(out_path)

    with open(os.path.join(panels_dir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_log, f, ensure_ascii=False, indent=2)
    return comic_dir


def export_prompts(script, cfgs):
    """APIを呼ばず、Google AI Studioで手動生成するためのプロンプト・参照画像・
    手順書を output/<id>/prompts/ に書き出す。画像生成そのものは行わない。"""
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    prompts_dir = os.path.join(comic_dir, "prompts")
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(prompts_dir, exist_ok=True)
    os.makedirs(panels_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    provider_name = gen_cfg.get("provider", "gemini")
    use_prev = gen_cfg.get("use_previous_panels_as_reference")
    panels_rel = os.path.relpath(panels_dir, cfglib.ROOT)

    for i, panel in enumerate(script["panels"], 1):
        prompt = build_prompt(script, panel, cfgs, provider_name)

        char_refs = []
        for key in panel.get("characters") or []:
            char = cfgs["characters"].get(key) or {}
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

    if provider_name == "comfyui":
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
    else:
        cfg = gen_cfg.get("gemini", {})
        readme_lines = [
            f"=== {script['id']} を Google AI Studio (aistudio.google.com) で手動生成する手順 ===",
            "",
            f"1. Nano Banana系の画像生成モデル（設定上は {cfg.get('model')}）のチャットを開く。",
            "2. アスペクト比は " + gen_cfg.get("aspect_ratio", "1:1")
            + (f"、画像サイズは {cfg['image_size']}" if cfg.get("image_size") else "")
            + " を選ぶ（AI StudioのUIに設定項目があれば）。",
            "3. panel_N.txt の中身をそのままプロンプトとして貼り付け、末尾に[添付する...]の",
            "   注記があれば同じ番号の panel_N_refs/ 内の画像を全て添付してから生成する。",
            f"4. 気に入った画像を {panels_rel}/panel_N.png として保存する（Nと採番を一致させること）。",
        ]
        if use_prev:
            readme_lines.append(
                "5. このスタイルは前コマ参照が有効。panel_2以降はprompt末尾の注記に従い、"
                "直前1〜2コマの完成画像も参照画像として追加で添付すること。")
        readme_lines += [
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
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    if args.export_prompts:
        export_prompts(script, cfgs)
    else:
        generate(script, cfgs, mock=args.mock)


if __name__ == "__main__":
    main()
