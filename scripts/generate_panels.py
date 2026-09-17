"""プロンプト書き出しとmock画像生成。

ローカル画像生成プロバイダは持たない。実画像は外部ツールで生成し、
scripts/accept_external_panel.py で accepted panel として取り込む。
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
import embed_text  # noqa: E402

_SPACE_HINTS = {
    "top": "the top area of the image",
    "top-left": "the upper-left area of the image",
    "top-right": "the upper-right area of the image",
    "bottom": "the bottom area of the image",
    "bottom-left": "the lower-left area of the image",
    "bottom-right": "the lower-right area of the image",
    "center": "the center of the image",
}


def prompt_profile(cfgs):
    generation = cfgs["style"].get("generation") or {}
    return generation.get("prompt_profile") or generation.get("provider") or "default"


def lookup_character(key, script, cfgs):
    local = (script.get("local_characters") or {}).get(key)
    if local:
        return local
    return cfgs["characters"].get(key)


def character_prompt_line(key, char):
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


def build_prompt(script, panel, cfgs, profile_name=None, panel_idx=None):
    style = cfgs["style"]
    profile_name = profile_name or prompt_profile(cfgs)
    try:
        prompt_style = style["prompt"][profile_name]
    except KeyError as exc:
        raise KeyError(f"unknown prompt profile {profile_name!r} in config/style.yaml") from exc

    parts = [prompt_style["style_prompt"].strip()]

    descs = []
    for key in panel.get("characters") or []:
        char = lookup_character(key, script, cfgs)
        if not char:
            raise ValueError(
                f"{script['id']}: panel character key '{key}' not found in "
                "local_characters or config/characters.yaml")
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
        parts.append(
            "Source context (not visible writing) — background facts this image "
            "must stay consistent with, but do not necessarily depict all of at "
            "once: \"" + caption_en.strip() + "\". Depict the single moment "
            "described in the Scene below; that moment should be one instance of "
            "these facts, not a different or unrelated event. Do NOT render this "
            "sentence, or any text, as writing anywhere in the image.")

    parts.append("Scene: " + panel["scene"].strip())

    hints = []
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
        parts.append("Leave calm, uncluttered empty background space in "
                     + " and ".join(dict.fromkeys(hints))
                     + " — this area will have text overlaid on top of it "
                       "afterward by separate compositing, so keep faces, hands, "
                       "and essential props outside it, and do not draw any "
                       "bubble, box, frame, or outlined shape there yourself.")

    parts.append(prompt_style["composition_rules"].strip())
    parts.append(prompt_style["no_text_rules"].strip())
    return "\n\n".join(parts)


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
    by_panel = {e["panel"]: e for e in existing}
    for entry in new_entries:
        by_panel[entry["panel"]] = entry
    return [by_panel[k] for k in sorted(by_panel)]


def _real_generation_removed():
    raise RuntimeError(
        "Local image generation providers have been removed. "
        "Run `python scripts/run_pipeline.py --id <id> --export-prompts`, "
        "generate square images externally, then import accepted images with "
        "`python scripts/accept_external_panel.py --id <id> --panel <N> --source <image>`.")


def generate(script, cfgs, mock=False, panel=None):
    """mock時だけpanel_N.pngを作る。実画像生成は外部ツールに委譲する。"""
    _check_panel_index(script, panel)
    if not mock:
        _real_generation_removed()

    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(panels_dir, exist_ok=True)

    n = len(script["panels"])
    targets = [panel] if panel else list(range(1, n + 1))
    profile = prompt_profile(cfgs)
    prompts_log = []
    for i in targets:
        prompt = build_prompt(script, script["panels"][i - 1], cfgs, profile, panel_idx=i - 1)
        prompts_log.append({"panel": i, "prompt": prompt})
        out_path = os.path.join(panels_dir, f"panel_{i}.png")
        make_mock_panel(i).save(out_path)
        print(f"[mock] panel {i}/{n} -> {os.path.relpath(out_path, cfglib.ROOT)}")

    prompts_path = os.path.join(panels_dir, "prompts.json")
    existing_log = []
    if os.path.exists(prompts_path):
        with open(prompts_path, encoding="utf-8") as f:
            existing_log = json.load(f)
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(_merge_prompts_log(existing_log, prompts_log), f, ensure_ascii=False, indent=2)
    return comic_dir


def _next_variant_start(temp_dir, panel_index):
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
    """mock候補だけをpanels_tempに作る。実候補生成は外部ツールに委譲する。"""
    _check_panel_index(script, panel)
    if not mock:
        _real_generation_removed()

    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    temp_dir = os.path.join(comic_dir, "panels_temp")
    os.makedirs(temp_dir, exist_ok=True)
    n = len(script["panels"])
    targets = [panel] if panel else list(range(1, n + 1))
    profile = prompt_profile(cfgs)
    prompts_log = []
    candidates_path = os.path.join(temp_dir, "candidates.jsonl")

    for i in targets:
        panel_data = script["panels"][i - 1]
        prompt = build_prompt(script, panel_data, cfgs, profile, panel_idx=i - 1)
        prompts_log.append({"panel": i, "prompt": prompt})
        start = _next_variant_start(temp_dir, i)
        for offset in range(count):
            v = start + offset
            image_name = f"panel_{i}_v{v}.png"
            out_path = os.path.join(temp_dir, image_name)
            make_mock_panel(i).save(out_path)
            with open(candidates_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "image": image_name,
                    "panel": i,
                    "scene": panel_data["scene"],
                    "prompt": prompt,
                    "seed": None,
                    "provider": "mock",
                    "mock": True,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, ensure_ascii=False) + "\n")
            print(f"[mock] panel {i}/{n} variant v{v} -> {os.path.relpath(out_path, cfglib.ROOT)}")

    prompts_path = os.path.join(temp_dir, "prompts.json")
    existing_log = []
    if os.path.exists(prompts_path):
        with open(prompts_path, encoding="utf-8") as f:
            existing_log = json.load(f)
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(_merge_prompts_log(existing_log, prompts_log), f, ensure_ascii=False, indent=2)
    return temp_dir


def _copy_reference_images(script, panel, cfgs, prompts_dir, panel_index):
    char_refs = []
    for key in panel.get("characters") or []:
        char = lookup_character(key, script, cfgs) or {}
        for rel in char.get("reference_images") or []:
            src = cfglib.rootpath(rel)
            if os.path.exists(src):
                char_refs.append((key, src))
    if not char_refs:
        return []

    refs_dir = os.path.join(prompts_dir, f"panel_{panel_index}_refs")
    os.makedirs(refs_dir, exist_ok=True)
    copied = []
    for idx, (key, src) in enumerate(char_refs, 1):
        ext = os.path.splitext(src)[1] or ".png"
        dest = os.path.join(refs_dir, f"{idx:02d}_{key}{ext}")
        shutil.copyfile(src, dest)
        copied.append(os.path.relpath(dest, cfglib.ROOT))
    return copied


def export_prompts(script, cfgs):
    """外部画像生成ツールへ渡すプロンプト・参照画像・manifestを書き出す。"""
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    prompts_dir = os.path.join(comic_dir, "prompts")
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(prompts_dir, exist_ok=True)
    os.makedirs(panels_dir, exist_ok=True)

    layout = cfgs["layout"]
    target_size = [int(layout["panel"]["width"]), int(layout["panel"]["height"])]
    if target_size[0] != target_size[1]:
        raise ValueError(f"external image handoff requires square panel size, got {target_size}")
    use_prev = (cfgs["style"].get("generation") or {}).get("use_previous_panels_as_reference")
    profile = prompt_profile(cfgs)
    manifest = {
        "id": script["id"],
        "prompt_profile": profile,
        "target_size": target_size,
        "aspect_ratio": "1:1",
        "panels": [],
    }

    for i, panel in enumerate(script["panels"], 1):
        prompt = build_prompt(script, panel, cfgs, profile, panel_idx=i - 1)
        prompt_path = os.path.join(prompts_dir, f"panel_{i}.txt")
        ref_paths = _copy_reference_images(script, panel, cfgs, prompts_dir, i)

        note_lines = [
            f"[Required output: a single square image, exactly {target_size[0]}x{target_size[1]} px after acceptance]",
            "[Do not generate a page, strip, border, caption, speech bubble, or any text.]",
        ]
        if ref_paths:
            note_lines.append(f"[Reference images copied under output/{script['id']}/prompts/panel_{i}_refs/.]")
        if use_prev and i > 1:
            prev_ids = [p for p in range(max(1, i - 2), i)]
            note_lines.append("[Optional previous-panel references: "
                              + ", ".join(f"panels/panel_{p}.png" for p in prev_ids)
                              + " if already accepted.]")

        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt + "\n\n" + "\n".join(note_lines) + "\n")

        manifest["panels"].append({
            "panel": i,
            "prompt_file": os.path.relpath(prompt_path, cfglib.ROOT),
            "reference_files": ref_paths,
            "scene": panel["scene"],
        })
        print(f"[export] panel {i}/{len(script['panels'])} -> {os.path.relpath(prompt_path, cfglib.ROOT)}")

    readme_lines = [
        f"=== {script['id']} external image generation handoff ===",
        "",
        f"Generate one square image per panel. Accepted target: {target_size[0]}x{target_size[1]} px.",
        "Do not generate a page/strip/grid. Do not include captions, speech bubbles, logos, or text.",
        "",
        "Recommended flow:",
        "1. Use panel_N.txt as the prompt for an external image generator.",
        "2. Save the returned image anywhere locally.",
        "3. Import the accepted image:",
        f"   python scripts/accept_external_panel.py --id {script['id']} --panel N --source <image-path>",
        "4. Repeat for all panels.",
        f"5. Run: python scripts/run_pipeline.py --id {script['id']} --skip-generate",
    ]
    readme_path = os.path.join(prompts_dir, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines) + "\n")

    manifest_path = os.path.join(prompts_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[export] manifest -> {os.path.relpath(manifest_path, cfglib.ROOT)}")
    return prompts_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--export-prompts", action="store_true",
                    help="APIを呼ばず外部画像生成向けにプロンプト・参照画像を書き出す")
    ap.add_argument("--variants", type=int,
                    help="mock候補だけをpanels_temp/に生成する（実画像生成には使わない）")
    ap.add_argument("--panel", type=int,
                    help="指定したコマ番号（1始まり）だけ処理する。省略時は全コマ")
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
