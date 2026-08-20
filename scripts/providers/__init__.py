"""画像生成プロバイダのレジストリ。

各プロバイダは scripts/providers/<name>/ フォルダにまとまっており、
generate_image(prompt, ref_images, gen_cfg) -> PIL.Image を提供する。
gen_cfg は config/style.yaml の generation セクション全体（provider共通キー +
gen_cfg[<name>] のプロバイダ固有設定）。

新しいプロバイダを足す場合: scripts/providers/<name>/ を作って
generate_image() を実装し、下のPROVIDERSに登録する。
"""
from . import comfyui, gemini

PROVIDERS = {
    "gemini": gemini,
    "comfyui": comfyui,
}


def get(name):
    if name not in PROVIDERS:
        raise ValueError(
            f"unknown generation provider: {name!r} (choices: {', '.join(PROVIDERS)})")
    return PROVIDERS[name]
