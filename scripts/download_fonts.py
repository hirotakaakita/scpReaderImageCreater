"""config/languages.yaml のdownloads定義に従いフォントを取得する。

fonts/ はgit管理外。GitHub Actionsではactions/cacheでキャッシュされる。
"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def main():
    lang_cfg = cfglib.load_configs()["languages"]
    for item in lang_cfg.get("downloads") or []:
        dest = cfglib.rootpath(item["dest"])
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            print(f"[fonts] exists: {item['dest']}")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"[fonts] downloading {item['url']}")
        r = requests.get(item["url"], timeout=300)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        print(f"[fonts] saved {item['dest']} ({len(r.content) // 1024} KB)")


if __name__ == "__main__":
    main()
