"""output/ を走査してアプリ/bot向け index.json を更新する。"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402

SCHEMA_VERSION = 1


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
            entries.append({
                "id": meta["id"],
                "revision": meta.get("revision", 1),
                "title": meta.get("title") or {},
                "languages": meta.get("languages") or [],
                "panels": meta.get("panels"),
                "createdAt": meta.get("created_at"),
                "basePath": f"output/{meta['id']}/base.png",
                "imagePathTemplate": f"output/{meta['id']}/{{lang}}.png",
                "thumbnailPath": f"output/{meta['id']}/thumbnail.png",
                "attribution": meta.get("attribution") or {},
            })
    entries.sort(key=lambda e: e.get("createdAt") or "", reverse=True)
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
