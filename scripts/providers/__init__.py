"""画像生成プロバイダのレジストリ。

各プロバイダは scripts/providers/<name>/ フォルダにまとまっており、
generate_image(prompt, ref_images, gen_cfg) -> (PIL.Image, seed:int) を提供する。
gen_cfg は config/style.yaml の generation セクション全体（provider共通キー +
gen_cfg[<name>] のプロバイダ固有設定）。seedは実際に使われた値（configのseedが
-1=ランダムの場合も、実際に採番された値）を返す。候補生成時の再現・比較用。

新しいプロバイダを足す場合: scripts/providers/<name>/ を作って
generate_image() を実装し、下のPROVIDERSに登録する。
"""
from . import comfyui

PROVIDERS = {
    "comfyui": comfyui,
}


def get(name):
    if name not in PROVIDERS:
        raise ValueError(
            f"unknown generation provider: {name!r} (choices: {', '.join(PROVIDERS)})")
    return PROVIDERS[name]
