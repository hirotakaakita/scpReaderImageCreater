"""ローカルComfyUIのAPIで画像を生成するプロバイダ。"""
import copy
import io
import json
import os
import sys
import time
import uuid

import requests
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
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


def _upload_image(server, pil_image):
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    resp = requests.post(f"{server}/upload/image",
                         files={"image": ("ref.png", buf, "image/png")},
                         data={"overwrite": "true"}, timeout=30)
    resp.raise_for_status()
    return resp.json()["name"]


def _build_workflow(prompt, cfg, ref_images=None):
    workflow_path = cfglib.rootpath(cfg["workflow_path"])
    workflow = copy.deepcopy(_load_workflow(workflow_path))
    _find_by_title(workflow, "Positive Prompt")["inputs"]["text"] = prompt

    ref_node = _find_by_title(workflow, "Reference Image", required=False)
    if ref_node is not None and ref_images:
        server = cfg.get("server", "http://127.0.0.1:8188")
        ref_node["inputs"]["image"] = _upload_image(server, ref_images[0])

    neg_node = _find_by_title(workflow, "Negative Prompt", required=False)
    if neg_node is not None and "text" in (neg_node.get("inputs") or {}) \
            and cfg.get("negative_prompt") is not None:
        neg_node["inputs"]["text"] = cfg["negative_prompt"]

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

    style_lora_node = _find_by_title(workflow, "Style LoRA", required=False)
    if style_lora_node is not None and cfg.get("style_lora_name"):
        style_lora_node["inputs"]["lora_name"] = cfg["style_lora_name"]
        style_lora_node["inputs"]["strength_model"] = cfg.get("style_lora_strength", 1.0)

    latent_node = (_find_by_class(workflow, "EmptyLatentImage", required=False)
                  or _find_by_class(workflow, "EmptySD3LatentImage", required=False))
    if latent_node is not None:
        width = int(cfg.get("width", 1328))
        height = int(cfg.get("height", width))
        if width <= 0 or height <= 0:
            raise ValueError(f"invalid generation size: {width}x{height}")
        if width != height:
            raise ValueError(
                f"SCP panel generation must be square; configure equal width/height (got {width}x{height})")
        latent_node["inputs"]["width"] = width
        latent_node["inputs"]["height"] = height

    sampler_node = _find_by_class(workflow, "KSampler")
    seed = cfg.get("seed", -1)
    sampler_node["inputs"]["seed"] = uuid.uuid4().int & 0xFFFFFFFF if seed is None or seed < 0 else seed
    sampler_node["inputs"]["steps"] = cfg.get("steps", 30)
    sampler_node["inputs"]["cfg"] = cfg.get("cfg", 7.0)
    sampler_node["inputs"]["sampler_name"] = cfg.get("sampler_name", "dpmpp_2m")
    sampler_node["inputs"]["scheduler"] = cfg.get("scheduler", "karras")
    return workflow


def _queue_prompt(server, workflow, client_id):
    resp = requests.post(f"{server}/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=30)
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
        "filename": image_ref["filename"], "subfolder": image_ref.get("subfolder", ""),
        "type": image_ref.get("type", "output")}, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def generate_image(prompt, ref_images, gen_cfg):
    cfg = gen_cfg.get("comfyui", {})
    server = cfg.get("server", "http://127.0.0.1:8188")
    max_retries = cfg.get("max_retries", 3)
    retry_wait = cfg.get("retry_wait_seconds", 5)
    poll_interval = cfg.get("poll_interval_seconds", 2)
    timeout = cfg.get("timeout_seconds", 300)
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            workflow = _build_workflow(prompt, cfg, ref_images)
            seed = _find_by_class(workflow, "KSampler")["inputs"]["seed"]
            client_id = str(uuid.uuid4())
            prompt_id = _queue_prompt(server, workflow, client_id)
            result = _wait_for_result(server, prompt_id, poll_interval, timeout)
            save_node = _find_by_class(workflow, "SaveImage")
            save_node_id = next(nid for nid, n in workflow.items() if n is save_node)
            outputs = result.get("outputs", {}).get(save_node_id, {})
            images = outputs.get("images") or []
            if not images:
                raise RuntimeError(f"no image in ComfyUI output (status={result.get('status')})")
            image = _fetch_image(server, images[0])
            if image.width != image.height:
                raise RuntimeError(f"ComfyUI returned non-square image: {image.width}x{image.height}")
            return image, seed
        except Exception as e:
            last_err = e
        if attempt < max_retries:
            wait = retry_wait * attempt
            print(f"  attempt {attempt} failed ({last_err}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"image generation failed: {last_err}")
