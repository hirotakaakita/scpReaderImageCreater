"""Validate comic YAML files without invoking image generation."""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def collect_paths(paths, include_all=False):
    result = list(paths)
    if include_all:
        for directory in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
            result.extend(glob.glob(os.path.join(directory, "*.yaml")))
            result.extend(glob.glob(os.path.join(directory, "*.yml")))
    return sorted(dict.fromkeys(result))


def validate_paths(paths, strict_source=False):
    results = []
    for path in paths:
        try:
            cfglib.load_script(path, require_source=strict_source)
            results.append({"path": path, "ok": True, "error": None})
        except Exception as exc:  # keep validating remaining files
            results.append({"path": path, "ok": False, "error": str(exc)})
    failures = [item for item in results if not item["ok"]]
    return {
        "ok": not failures,
        "checked": len(results),
        "failures": len(failures),
        "strictSource": strict_source,
        "results": results,
    }


def print_human(payload, quiet=False):
    label = "valid+source" if payload["strictSource"] else "valid"
    if quiet:
        if payload["ok"]:
            print(f"OK: validated {payload['checked']} script(s)")
        else:
            print(f"FAIL: {payload['failures']}/{payload['checked']} script(s) invalid")
            for item in payload["results"]:
                if not item["ok"]:
                    print(f"- {item['path']}: {item['error']}", file=sys.stderr)
        return

    for item in payload["results"]:
        if item["ok"]:
            print(f"[{label}] {item['path']}")
        else:
            print(f"[invalid] {item['path']}: {item['error']}", file=sys.stderr)
    if payload["ok"]:
        print(f"Validated {payload['checked']} script(s).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="YAML files to validate")
    ap.add_argument("--all", action="store_true",
                    help="validate all queue/done YAML files")
    ap.add_argument("--strict-source", action="store_true",
                    help="require panels[].source provenance on every panel")
    ap.add_argument("--json", dest="json_output", action="store_true",
                    help="print compact machine-readable result")
    ap.add_argument("--quiet", action="store_true",
                    help="print only a summary and errors")
    args = ap.parse_args()

    paths = collect_paths(args.paths, include_all=args.all)
    if not paths:
        ap.error("provide YAML path(s) or --all")

    payload = validate_paths(paths, strict_source=args.strict_source)
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload, quiet=args.quiet)
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
