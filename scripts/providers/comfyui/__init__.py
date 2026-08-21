"""ローカルComfyUIのAPIで画像を生成するプロバイダ。

generate_panels.py から generate_image(prompt, ref_images, gen_cfg) が呼ばれる。
gemini プロバイダ（scripts/providers/gemini/）と同じインターフェースで、
config/style.yaml の generation.provider: comfyui を指定すると自動的にこちらが使われる。

前提: ComfyUIをローカルで起動しておくこと（既定 http://127.0.0.1:8188）。
設定・セットアップ手順は README.md 参照。
"""
import copy
import io
import json
import os
import sys
import time
import uuid

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # -> scripts/
from lib import config as cfglib  # noqa: E402

_WORKFLOW_CACHE = {}


def _load_workflow(path):
    if path not in _WORKFLOW_CACHE:
        with open(path, encoding="utf-8") as f:
            _WORKFLOW_CACHE[path] = json.load(f)
    return _WORKFLOW_CACHE[path]


def _find_by_title(workflow, title, required=True):
    for node_id, node in workflow.items():
        if (node.get("_meta") or {}).get("title") == title:
            return node
    if required:
        raise KeyError(f"workflow_api.json has no node titled {title!r}")
    return None


def _find_by_class(workflow, class_type, required=True):
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return node
    if required:
        raise KeyError(f"workflow_api.json has no node of class_type={class_type!r}")
    return None


def _build_workflow(prompt, cfg):
    workflow_path = cfglib.rootpath(cfg["workflow_path"])
    workflow = copy.deepcopy(_load_workflow(workflow_path))

    _find_by_title(workflow, "Positive Prompt")["inputs"]["text"] = prompt

    # ネガティブプロンプトは無いモデル向けワークフローもある（例: Z-Image Turboの公式
    # テンプレートはConditioningZeroOutでネガティブを代用しており、textノードが無い）
    neg_node = _find_by_title(workflow, "Negative Prompt", required=False)
    if neg_node is not None and "text" in (neg_node.get("inputs") or {}) \
            and cfg.get("negative_prompt") is not None:
        neg_node["inputs"]["text"] = cfg["negative_prompt"]

    # モデル読み込みノードはアーキテクチャによって異なる:
    #   SDXL系: CheckpointLoaderSimple（1ファイル）
    #   Z-Image Turbo等の新しめのモデル: UNETLoader + CLIPLoader + VAELoader（3ファイル別々）
    # ワークフローに存在するノードだけ、対応するconfigキーがあれば書き換える。
    ckpt_node = _find_by_class(workflow, "CheckpointLoaderSimple", required=False)
    if ckpt_node is not None and cfg.get("checkpoint"):
        ckpt_node["inputs"]["ckpt_name"] = cfg["checkpoint"]

    unet_node = _find_by_class(workflow, "UNETLoader", required=False)
    if unet_node is not None and cfg.get("unet_name"):
        unet_node["inputs"]["unet_name"] = cfg["unet_name"]

    clip_node = _find_by_class(workflow, "CLIPLoader", required=False)
    if clip_node is not None and cfg.get("clip_name"):
        clip_node["inputs"]["clip_name"] = cfg["clip_name"]

    vae_node = _find_by_class(workflow, "VAELoader", required=False)
    if vae_node is not None and cfg.get("vae_name"):
        vae_node["inputs"]["vae_name"] = cfg["vae_name"]

    # 潜在画像サイズのノードもモデルによってクラス名が異なる
    latent_node = (_find_by_class(workflow, "EmptyLatentImage", required=False)
                  or _find_by_class(workflow, "EmptySD3LatentImage", required=False))
    if latent_node is not None:
        latent_node["inputs"]["width"] = cfg.get("width", 1024)
        latent_node["inputs"]["height"] = cfg.get("height", 1024)

    sampler_node = _find_by_class(workflow, "KSampler")
    seed = cfg.get("seed", -1)
    sampler_node["inputs"]["seed"] = uuid.uuid4().int & 0xFFFFFFFF if seed is None or seed < 0 else seed
    sampler_node["inputs"]["steps"] = cfg.get("steps", 30)
    sampler_node["inputs"]["cfg"] = cfg.get("cfg", 7.0)
    sampler_node["inputs"]["sampler_name"] = cfg.get("sampler_name", "dpmpp_2m")
    sampler_node["inputs"]["scheduler"] = cfg.get("scheduler", "karras")

    return workflow


def _queue_prompt(server, workflow, client_id):
    resp = requests.post(f"{server}/prompt",
                         json={"prompt": workflow, "client_id": client_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _wait_for_result(server, prompt_id, poll_interval, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{server}/history/{prompt_id}", timeout=30)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI generation timed out after {timeout}s (prompt_id={prompt_id})")


def _fetch_image(server, image_ref):
    resp = requests.get(f"{server}/view", params={
        "filename": image_ref["filename"],
        "subfolder": image_ref.get("subfolder", ""),
        "type": image_ref.get("type", "output"),
    }, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def generate_image(prompt, ref_images, gen_cfg):
    """ref_imagesは現状無視される（汎用txt2imgワークフローは画像入力に非対応のため）。
    キャラクター一貫性を上げたい場合はワークフローにIPAdapter等を組み込み、
    このプロバイダを拡張すること。"""
    cfg = gen_cfg.get("comfyui", {})
    if ref_images:
        print(f"  [comfyui] NOTE: {len(ref_images)} reference image(s) ignored "
              "(workflow_api.json has no image input node)")

    server = cfg.get("server", "http://127.0.0.1:8188")
    max_retries = cfg.get("max_retries", 3)
    retry_wait = cfg.get("retry_wait_seconds", 5)
    poll_interval = cfg.get("poll_interval_seconds", 2)
    timeout = cfg.get("timeout_seconds", 300)

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            workflow = _build_workflow(prompt, cfg)
            client_id = str(uuid.uuid4())
            prompt_id = _queue_prompt(server, workflow, client_id)
            result = _wait_for_result(server, prompt_id, poll_interval, timeout)

            save_node = _find_by_class(workflow, "SaveImage")
            save_node_id = next(nid for nid, n in workflow.items() if n is save_node)
            outputs = result.get("outputs", {}).get(save_node_id, {})
            images = outputs.get("images") or []
            if not images:
                raise RuntimeError(f"no image in ComfyUI output (status={result.get('status')})")
            return _fetch_image(server, images[0])
        except Exception as e:  # 接続エラー・タイムアウト・ノード不備を含む
            last_err = e
        wait = retry_wait * attempt
        print(f"  attempt {attempt} failed ({last_err}); retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"image generation failed: {last_err}")


def _find_grid_lines(darkness, count, total):
    """darkness: 軸方向の各画素列(行)の暗さの1次元配列。count-1本の境界線の
    実際の位置を、均等割りの想定位置の近傍で最も暗い（=AIが描いた黒枠線に
    最も近い）位置にスナップさせて返す。"""
    positions = []
    cell = total / count
    margin = max(4, int(cell * 0.15))
    for i in range(1, count):
        expected = int(round(i * cell))
        lo, hi = max(0, expected - margin), min(total, expected + margin)
        window = darkness[lo:hi]
        positions.append(lo + int(window.argmax()) if window.size else expected)
    return positions


def _split_grid(img, cols, rows):
    """画像をrows x colsのコマに分割する。

    単純に幅・高さをcols/rows等分すると、AIが描いた黒枠線の実際の位置は
    生成のたびに数〜十数px単位でズレるため、境界がコマの片側にだけ残ったり
    どちらにも残らなかったりして「コマの位置が左右にずれて見える」原因に
    なっていた。ここでは列・行ごとの明度から黒枠線の実位置を検出し、その
    線の中心で切ることでズレを防ぐ。
    """
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = gray.shape
    darkness_x = 255.0 - gray.mean(axis=0)  # 列ごとの暗さ（縦の枠線を探す）
    darkness_y = 255.0 - gray.mean(axis=1)  # 行ごとの暗さ（横の枠線を探す）
    xs = [0] + _find_grid_lines(darkness_x, cols, w) + [w]
    ys = [0] + _find_grid_lines(darkness_y, rows, h) + [h]

    crops = []
    for r in range(rows):
        for c in range(cols):
            crops.append(img.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])))
    return crops


def generate_page(prompt, cols, rows, gen_cfg):
    """全コマ分を1枚のグリッド画像として生成し、rows x cols で分割して返す。

    generation.comfyui.page_mode: true のときに generate_panels.py から呼ばれる。
    戻り値は行優先（左上→右上→...→左下→右下）のPIL.Imageリスト。
    1回の生成で全コマを描かせる方式で、Z-Image Turboは単一シーン指示より
    こちらの方が文字焼き込み無しで安定することを確認済み（README参照）。
    """
    img = generate_image(prompt, [], gen_cfg)
    return _split_grid(img, cols, rows)
