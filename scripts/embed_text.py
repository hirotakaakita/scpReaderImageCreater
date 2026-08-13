"""base.pngに言語別のタイトル・吹き出しテキストを埋め込む。

output/<id>/<lang>.png を対応言語分生成する。
吹き出しの位置は台本の position（プリセット名 or 正規化座標）で固定される。
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
from lib import drawing  # noqa: E402


def resolve_area(position, presets):
    if isinstance(position, dict):
        return position
    if position in presets:
        return presets[position]
    raise ValueError(f"unknown bubble position: {position}")


def title_for(script, lang):
    titles = script.get("title") or {}
    return titles.get(lang) or titles.get("en") or script["id"].upper()


def subtitle_for(script, lang, lang_cfg):
    object_class = script.get("object_class")
    if not object_class:
        return None
    label = (lang_cfg.get("object_class_label") or {}).get(lang) \
        or (lang_cfg.get("object_class_label") or {}).get("en") or "Object Class: "
    return f"{label}{object_class}"


def embed(script, cfgs, languages=None):
    layout = cfgs["layout"]
    lang_cfg = cfgs["languages"]
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    base = Image.open(os.path.join(comic_dir, "base.png"))
    with open(os.path.join(comic_dir, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)

    langs = languages or lang_cfg["languages"]
    fallback_path = cfglib.rootpath(lang_cfg["fonts"]["default"])
    generated = []
    for lang in langs:
        font_path = cfglib.font_path_for(lang, lang_cfg)
        if not os.path.exists(font_path):
            print(f"[embed] WARN: font missing for {lang} ({font_path}); skipped")
            continue
        char_wrap = cfglib.is_char_wrap(lang, lang_cfg)

        img = base.copy()
        draw = ImageDraw.Draw(img)
        drawing.draw_header_text(draw, meta["header_rect"], title_for(script, lang),
                                 font_path, layout["header"],
                                 subtitle=subtitle_for(script, lang, lang_cfg),
                                 fallback_path=fallback_path)

        for idx, panel in enumerate(script["panels"]):
            rect = meta["panel_rects"][idx]
            caption_text = (panel.get("caption") or {}).get(lang) \
                or (panel.get("caption") or {}).get("en")
            caption_rects = meta.get("caption_rects") or []
            caption_rect = caption_rects[idx] if idx < len(caption_rects) else None
            if caption_text and caption_rect:
                fits = drawing.draw_caption_text(
                    draw, caption_rect, caption_text, font_path,
                    layout["caption"], char_wrap=char_wrap,
                    fallback_path=fallback_path)
                if not fits:
                    print(f"[embed] WARN: text overflow {script['id']} "
                          f"panel {idx + 1} caption lang={lang}")
            for bubble in panel.get("bubbles") or []:
                text = (bubble.get("text") or {}).get(lang) \
                    or (bubble.get("text") or {}).get("en")
                if not text:
                    continue
                area = resolve_area(bubble.get("position", "top"),
                                    layout["bubble_presets"])
                fits = drawing.draw_speech(
                    draw, rect, area, text, font_path, layout["bubble"],
                    tail=bubble.get("tail"), char_wrap=char_wrap,
                    fallback_path=fallback_path)
                if not fits:
                    print(f"[embed] WARN: text overflow {script['id']} "
                          f"panel {idx + 1} lang={lang}")

        addendum = script.get("addendum") or {}
        addendum_text = addendum.get(lang) or addendum.get("en")
        if addendum_text and meta.get("addendum_rect"):
            fits = drawing.draw_caption_text(
                draw, meta["addendum_rect"], addendum_text, font_path,
                layout["addendum"], char_wrap=char_wrap,
                fallback_path=fallback_path)
            if not fits:
                print(f"[embed] WARN: text overflow {script['id']} "
                      f"addendum lang={lang}")

        out = os.path.join(comic_dir, f"{lang}.png")
        img.save(out)
        generated.append(lang)

    meta["languages"] = generated
    with open(os.path.join(comic_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=True, indent=2)
    print(f"[embed] {len(generated)} languages: {', '.join(generated)}")
    return generated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    ap.add_argument("--languages", help="カンマ区切り (例: ja,en)")
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    langs = args.languages.split(",") if args.languages else None
    embed(script, cfgs, languages=langs)


if __name__ == "__main__":
    main()
