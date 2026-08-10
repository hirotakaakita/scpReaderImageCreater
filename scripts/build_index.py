"""output/ を走査してindex.jsonを更新する。

アプリ・Twitter bot はこのindex.jsonから漫画の一覧と画像URLを引ける。
raw.githubusercontent.com がcharset無しで配信するため、非ASCIIは
\\uXXXX エスケープで出力する（scpjpReaderActionsと同じ方針）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def build():
    entries = []
    if os.path.isdir(cfglib.OUTPUT_DIR):
        for name in sorted(os.listdir(cfglib.OUTPUT_DIR)):
            meta_path = os.path.join(cfglib.OUTPUT_DIR, name, "meta.json")
            if not os.path.exists(meta_path):
                continue
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            entries.append({
                "id": meta["id"],
                "title": meta.get("title") or {},
                "languages": meta.get("languages") or [],
                "panels": meta.get("panels"),
                "createdAt": meta.get("created_at"),
                "basePath": f"output/{meta['id']}/base.png",
                "imagePathTemplate": f"output/{meta['id']}/{{lang}}.png",
                "attribution": meta.get("attribution") or {},
            })
    entries.sort(key=lambda e: e.get("createdAt") or "", reverse=True)
    index_path = cfglib.rootpath("index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"comics": entries}, f, ensure_ascii=True, indent=2)
    print(f"[index] {len(entries)} comics -> index.json")


if __name__ == "__main__":
    build()
