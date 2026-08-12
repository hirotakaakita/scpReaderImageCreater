"""Nano Banana / Nano Banana Pro (Gemini画像生成) で各コマの画像を生成する。

台本のscene + config/style.yaml(絵柄) + config/characters.yaml(キャラ定義)から
プロンプトを組み立て、output/<id>/panels/panel_N.png に保存する。
テキスト・吹き出しは一切描かせない（後工程のembed_text.pyが埋め込む）。

呼び出し先は config/style.yaml の generation.provider で切り替える:
  provider: gemini      -> Google AI Studio直接（google-genai SDK, GEMINI_API_KEY）
  provider: openrouter  -> OpenRouter経由（requests, OPENROUTER_API_KEY）
どちらも同じGeminiモデルを叩くが、課金の入口が異なる
（GCPの請求先アカウント紐付け vs OpenRouterアカウントへのクレジット入金）。

--mock を付けるとAPIを呼ばずプレースホルダー画像を生成する（レイアウト確認用）。
"""
import argparse
import base64
import io
import json
import os
import sys
import time

import requests
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402

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


def build_prompt(script, panel, cfgs):
    style = cfgs["style"]
    characters = cfgs["characters"]
    parts = [style["style_prompt"].strip()]

    names = panel.get("characters") or []
    descs = []
    for key in names:
        if key in characters:
            descs.append(characters[key]["description"].strip())
    if descs:
        parts.append("Characters appearing in this panel (keep these designs exactly consistent):\n- "
                     + "\n- ".join(descs))

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

    parts.append(style["composition_rules"].strip())
    parts.append(style["no_text_rules"].strip())
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


def _image_config(gen_cfg):
    cfg = {"aspect_ratio": gen_cfg.get("aspect_ratio", "1:1")}
    if gen_cfg.get("image_size"):  # image_sizeはPro系のみ対応。null時は送らない
        cfg["image_size"] = gen_cfg["image_size"]
    return cfg


def _retry_loop(gen_cfg, attempt_fn):
    """attempt_fn()を呼び、成功したらPIL Imageを返す。失敗はリトライ、
    課金不足など回復不能なエラーは即座に投げ直す。"""
    last_err = None
    for attempt in range(1, gen_cfg.get("max_retries", 3) + 1):
        try:
            return attempt_fn()
        except _Fatal:
            raise
        except Exception as e:  # レート制限・一時エラーを含む
            last_err = e
        wait = gen_cfg.get("retry_wait_seconds", 20) * attempt
        print(f"  attempt {attempt} failed ({last_err}); retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"image generation failed: {last_err}")


class _Fatal(Exception):
    """リトライしても無駄なエラー（課金未設定など）。"""


def call_gemini_direct(prompt, ref_images, gen_cfg):
    """Google AI Studio直接（google-genai SDK）。GEMINI_API_KEYが必要。"""
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [prompt] + list(ref_images)
    gen_config = {
        "response_modalities": ["TEXT", "IMAGE"],
        "image_config": _image_config(gen_cfg),
    }

    def attempt():
        resp = client.models.generate_content(
            model=gen_cfg["model"], contents=contents, config=gen_config)
        for cand in resp.candidates or []:
            for part in cand.content.parts or []:
                data = getattr(part, "inline_data", None)
                if data and data.data:
                    return Image.open(io.BytesIO(data.data))
        raise RuntimeError("no image in response")

    return _retry_loop(gen_cfg, attempt)


def _to_data_url(img):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def call_openrouter(prompt, ref_images, gen_cfg):
    """OpenRouter経由（chat completions API）。OPENROUTER_API_KEYが必要。
    同じGeminiモデルを、GCPの請求先アカウント設定なしにOpenRouterの
    クレジット残高で呼べる（https://openrouter.ai/settings/credits）。"""
    api_key = os.environ["OPENROUTER_API_KEY"]
    model = gen_cfg["model"]
    if "/" not in model:
        model = f"google/{model}"  # OpenRouterのモデルスラッグは "google/" 接頭辞付き

    content = [{"type": "text", "text": prompt}]
    for img in ref_images:
        content.append({"type": "image_url", "image_url": {"url": _to_data_url(img)}})

    body = {
        "model": model,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": content}],
        "image_config": _image_config(gen_cfg),
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    def attempt():
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=body, timeout=180)
        if 400 <= resp.status_code < 500:
            # クライアントエラー（クレジット不足・モデル未許可・データポリシー未設定など）は
            # リトライしても直らないので即座に失敗させ、レスポンス本文をそのまま出す
            raise _Fatal(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
        images = ((data.get("choices") or [{}])[0].get("message") or {}).get("images") or []
        if not images:
            raise RuntimeError(f"no image in response: {json.dumps(data)[:300]}")
        url = images[0]["image_url"]["url"]
        return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))

    return _retry_loop(gen_cfg, attempt)


def call_generate(prompt, ref_images, gen_cfg):
    provider = gen_cfg.get("provider", "gemini")
    if provider == "openrouter":
        return call_openrouter(prompt, ref_images, gen_cfg)
    if provider == "gemini":
        return call_gemini_direct(prompt, ref_images, gen_cfg)
    raise ValueError(f"unknown generation.provider: {provider}")


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
    prompts_log = []
    prev_paths = []
    for i, panel in enumerate(script["panels"], 1):
        out_path = os.path.join(panels_dir, f"panel_{i}.png")
        prompt = build_prompt(script, panel, cfgs)
        prompts_log.append({"panel": i, "prompt": prompt})
        print(f"[generate] panel {i}/{len(script['panels'])}")
        if mock:
            img = make_mock_panel(i)
        else:
            refs = collect_reference_images(script, panel, cfgs, prev_paths)
            img = call_generate(prompt, refs, gen_cfg)
        img.convert("RGB").save(out_path)
        prev_paths.append(out_path)

    with open(os.path.join(panels_dir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_log, f, ensure_ascii=False, indent=2)
    return comic_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    generate(script, cfgs, mock=args.mock)


if __name__ == "__main__":
    main()
