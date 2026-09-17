"""Check that semantic text revisions touched every production language.

This is intentionally simple: it inspects the git diff for YAML language keys.
It catches the most common operational mistake: changing only ja/en after a
semantic caption/title/addendum edit.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def find_script(comic_id_or_path):
    if os.path.exists(comic_id_or_path):
        return comic_id_or_path
    for directory in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
        path = os.path.join(directory, f"{comic_id_or_path}.yaml")
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"script not found: {comic_id_or_path}")


def git_diff(path):
    proc = subprocess.run(["git", "diff", "--", path], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def touched_languages(diff, languages):
    pattern = re.compile(r"^\+\s*(" + "|".join(re.escape(l) for l in languages) + r"):\s*", re.MULTILINE)
    return set(pattern.findall(diff))


def check(path, expect, required_langs):
    cfglib.load_script(path)
    diff = git_diff(path)
    if not diff.strip():
        return ["no git diff found for script; cannot verify revision scope"]
    touched = touched_languages(diff, required_langs)

    if expect == "semantic-all-languages":
        missing = [lang for lang in required_langs if lang not in touched]
        if missing:
            return ["semantic text edit did not touch all production languages: " + ", ".join(missing)]
        return []

    if expect.endswith("-only"):
        lang = expect[:-len("-only")]
        if lang in required_langs and lang not in touched:
            return [f"expected {lang} to be touched, but git diff does not show it"]
        return []

    return [f"unknown expectation: {expect}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_or_path", help="comic id such as scp-173, or YAML path")
    ap.add_argument("--expect", default="semantic-all-languages",
                    help="semantic-all-languages, ja-only, en-only, etc.")
    ap.add_argument("--panel", help="document the intended target panel")
    ap.add_argument("--field", help="document the intended field: caption/title/addendum")
    args = ap.parse_args()

    path = find_script(args.comic_or_path)
    required_langs = list(cfglib.load_configs()["languages"].get("languages") or [])
    errors = check(path, args.expect, required_langs)
    if errors:
        print(f"[text-revision-check] FAIL {path}")
        if args.panel or args.field:
            print(f"target: panel={args.panel or '-'} field={args.field or '-'}")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"[text-revision-check] OK {path} ({args.expect})")


if __name__ == "__main__":
    main()
