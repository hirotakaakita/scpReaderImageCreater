"""ChatGPT Imagesに手渡すSCP漫画用の生成パケットを作る。"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import embed_text  # noqa: E402

_SPACE_HINTS = {
    "top": "the top area of the image", "top-left": "the upper-left area of the image",
    "top-right": "the upper-right area of the image", "bottom": "the bottom area of the image",
    "bottom-left": "the lower-left area of the image", "bottom-right": "the lower-right area of the image",
    "center": "the center of the image",
}


def lookup_character(key, script, cfgs):
    return (script.get("local_characters") or {}).get(key) or cfgs["characters"].get(key)


def character_prompt_line(key, char):
    appearance = char.get("appearance")
    if appearance:
        line = f"{key}: {appearance.strip()}"
        if char.get("default_look"):
            line += (" Default look (use this only if the Scene below does not specify "
                     f"different clothing/expression for this moment): {char['default_look'].strip()}")
        return line
    return f"{key}: {char['description'].strip()}"


def build_prompt(script, panel, cfgs, panel_idx=None):
    """ChatGPT Imagesへそのまま渡す、短縮しない完成プロンプト。"""
    prompt_style = cfgs["style"]["prompt"]
    parts = [prompt_style["style_prompt"].strip()]
    descriptions = []
    for key in panel.get("characters") or []:
        char = lookup_character(key, script, cfgs)
        if not char:
            raise ValueError(f"{script['id']}: panel character key '{key}' not found")
        descriptions.append(character_prompt_line(key, char))
    if descriptions:
        parts.append("Characters appearing in this image (their default appearance — keep "
                     "face, hair, and build exactly consistent with this at all times). If "
                     "the Scene description below explicitly describes different clothing, "
                     "protective gear, or accessories for this particular moment, the Scene "
                     "always overrides this default clothing — draw what the Scene says they "
                     "are wearing here, not the default outfit listed below:\n- " + "\n- ".join(descriptions))
    caption_en = (panel.get("caption") or {}).get("en")
    if caption_en:
        parts.append("Source context (not visible writing) — background facts this image "
                     "must stay consistent with, but do not necessarily depict all of at "
                     "once: \"" + caption_en.strip() + "\". Depict the single moment "
                     "described in the Scene below; that moment should be one instance of "
                     "these facts, not a different or unrelated event. Do NOT render this "
                     "sentence, or any text, as writing anywhere in the image.")
    parts.append("Scene: " + panel["scene"].strip())
    hints = []
    if panel_idx is not None and panel.get("caption"):
        position = embed_text.caption_position_for(panel, panel_idx, cfgs["layout"].get("caption", {}))
        if position in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[position])
    for bubble in panel.get("bubbles") or []:
        if bubble.get("position", "top") in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[bubble.get("position", "top")])
    if hints:
        parts.append("Leave calm, uncluttered empty background space in " + " and ".join(dict.fromkeys(hints))
                     + " — this area will have text overlaid on top of it afterward by separate "
                       "compositing, so keep faces, hands, and essential props outside it, and do "
                       "not draw any bubble, box, frame, or outlined shape there yourself.")
    parts.extend((prompt_style["composition_rules"].strip(), prompt_style["no_text_rules"].strip()))
    return "\n\n".join(parts)


def _copy_references(script, panel, cfgs, bundle_dir, panel_index):
    copied, seen = [], set()
    for key in panel.get("characters") or []:
        char = lookup_character(key, script, cfgs) or {}
        for relative in char.get("reference_images") or []:
            source = cfglib.rootpath(relative)
            if not os.path.isfile(source) or source in seen:
                continue
            seen.add(source)
            ext = os.path.splitext(source)[1] or ".png"
            relative_bundle = os.path.join("references", f"panel_{panel_index}", f"{len(copied)+1:02d}_{key}{ext}")
            destination = os.path.join(bundle_dir, relative_bundle)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(relative_bundle.replace("\\", "/"))
    return copied


def export_chatgpt_bundle(script, script_path, cfgs, destination=None):
    """画像を生成せず、対話型ChatGPT Images用の自己完結した入力一式を出力する。"""
    bundle_dir = destination or os.path.join(cfglib.OUTPUT_DIR, script["id"], "chatgpt-image-prompts")
    os.makedirs(bundle_dir, exist_ok=True)
    os.makedirs(os.path.join(cfglib.OUTPUT_DIR, script["id"], "panels"), exist_ok=True)
    for filename in ("style.yaml", "characters.yaml", "layout.yaml", "languages.yaml"):
        config_dir = os.path.join(bundle_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        shutil.copy2(cfglib.rootpath("config", filename), os.path.join(config_dir, filename))
    shutil.copy2(script_path, os.path.join(bundle_dir, "source.yaml"))
    entries = []
    for index, panel in enumerate(script["panels"], 1):
        prompt_name = f"panel_{index}.prompt.txt"
        with open(os.path.join(bundle_dir, prompt_name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(build_prompt(script, panel, cfgs, panel_idx=index - 1) + "\n")
        handoff = cfgs["style"].get("handoff", {})
        previous_count = handoff.get("max_previous_panels", 2)
        previous = ([f"../panels/panel_{n}.png" for n in range(max(1, index - previous_count), index)]
                    if handoff.get("use_previous_panels_as_reference", True) else [])
        entries.append({"panel": index, "prompt_file": prompt_name,
                        "save_generated_image_as": f"../panels/panel_{index}.png",
                        "character_reference_files": _copy_references(script, panel, cfgs, bundle_dir, index),
                        "previous_panel_references": previous})
    manifest = {"schema_version": 1, "comic_id": script["id"], "generator": "ChatGPT Images",
                "source_script": "source.yaml", "config_snapshots": "config/",
                "after_generation": f"python scripts/run_pipeline.py --id {script['id']} --compose",
                "panels": entries}
    with open(os.path.join(bundle_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    lines = [f"# {script['id']} — ChatGPT Images 入力パケット", "",
             "各 `panel_N.prompt.txt` はCodexが実際にChatGPT Imagesへ渡す完成プロンプトです。要約・言い換えをせず、ファイル全体をそのまま使用してください。", "",
             "1. panel_1から順番にChatGPTの画像生成で、対応する `.prompt.txt` の全文を入力する。",
             "2. `manifest.json` の `character_reference_files` があれば同時に添付する。panel_2以降は `previous_panel_references` の画像が存在すれば、それも添付して見た目を引き継ぐ。",
             "3. 完成画像を `save_generated_image_as` に指定された名前で保存する。画像内に文字は入れない。",
             "4. 全コマを保存した後、`after_generation` のコマンドで合成・各言語の文字埋め込みを行う。", "",
             "`source.yaml` と `config/` は、プロンプトを確認・修正するための入力スナップショットです。"]
    with open(os.path.join(bundle_dir, "README.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"[export] ChatGPT Images packet -> {os.path.relpath(bundle_dir, cfglib.ROOT)}")
    return bundle_dir
