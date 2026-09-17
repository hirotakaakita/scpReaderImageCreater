"""output/ を走査してアプリ/bot向け index.json を更新する。"""
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402

SCHEMA_VERSION = 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def asset(path):
    abs_path = cfglib.rootpath(path)
    if not os.path.exists(abs_path):
        return {"path": path, "missing": True}
    return {"path": path, "sha256": sha256_file(abs_path)}


def content_hash(assets):
    hashes = []
    for item in (assets.get("base"), assets.get("thumbnail")):
        if item and item.get("sha256"):
            hashes.append(item["sha256"])
    for lang, item in sorted((assets.get("languages") or {}).items()):
        if item.get("sha256"):
            hashes.append(f"{lang}:{item['sha256']}")
    return hashlib.sha256("\n".join(hashes).encode("utf-8")).hexdigest() if hashes else None


def build():
    entries = []
    if os.path.isdir(cfglib.OUTPUT_DIR):
        for name in sorted(os.listdir(cfglib.OUTPUT_DIR)):
            meta_path = os.path.join(cfglib.OUTPUT_DIR, name, "meta.json")
            if not os.path.exists(meta_path):
                continue
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            # Fail closed: only explicit True is publishable.
            if meta.get("complete") is not True:
                print(f"[index] skip {meta.get('id', name)}: not publish-complete")
                continue

            comic_id = meta["id"]
            languages = meta.get("languages") or []
            assets = {
                "base": asset(f"output/{comic_id}/base.png"),
                "thumbnail": asset(f"output/{comic_id}/thumbnail.png"),
                "languages": {
                    lang: asset(f"output/{comic_id}/{lang}.png")
                    for lang in languages
                },
            }
            digest = content_hash(assets)
            entries.append({
                "id": comic_id,
                "revision": meta.get("revision", 1),
                "contentHash": digest,
                "title": meta.get("title") or {},
                "languages": languages,
                "panels": meta.get("panels"),
                "createdAt": meta.get("created_at"),
                "updatedAt": meta.get("updated_at") or meta.get("created_at"),
                "basePath": f"output/{comic_id}/base.png",
                "imagePathTemplate": f"output/{comic_id}/{{lang}}.png",
                "thumbnailPath": f"output/{comic_id}/thumbnail.png",
                "assets": assets,
                "attribution": meta.get("attribution") or {},
            })
    entries.sort(key=lambda e: e.get("updatedAt") or e.get("createdAt") or "", reverse=True)
    index_path = cfglib.rootpath("index.json")
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "comics": entries,
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
    print(f"[index] schema v{SCHEMA_VERSION}, {len(entries)} comics -> index.json")
    return payload


if __name__ == "__main__":
    build()
