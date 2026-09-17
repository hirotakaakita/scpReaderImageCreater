"""Validate comic YAML files without invoking image generation."""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="YAML files to validate")
    ap.add_argument("--all", action="store_true",
                    help="validate all queue/done YAML files")
    args = ap.parse_args()

    paths = list(args.paths)
    if args.all:
        for directory in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
            paths.extend(glob.glob(os.path.join(directory, "*.yaml")))
            paths.extend(glob.glob(os.path.join(directory, "*.yml")))
    paths = sorted(dict.fromkeys(paths))
    if not paths:
        ap.error("provide YAML path(s) or --all")

    failures = 0
    for path in paths:
        try:
            cfglib.load_script(path)
            print(f"[valid] {path}")
        except Exception as exc:
            failures += 1
            print(f"[invalid] {path}: {exc}", file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print(f"Validated {len(paths)} script(s).")


if __name__ == "__main__":
    main()
