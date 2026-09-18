"""生成結果を指定パネルへ取り込み、検査・組版・任意のGit操作を一括で行う。"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import validate_comic  # noqa: E402


def parse_panel_files(values, count):
    mapping = {}
    for value in values:
        try:
            number, path = value.split("=", 1)
            number = int(number)
        except ValueError as exc:
            raise ValueError(f"--panel-file must be N=PATH (got {value!r})") from exc
        if number in mapping or not os.path.isfile(path):
            raise ValueError(f"invalid or duplicate panel file: {value}")
        mapping[number] = path
    expected = set(range(1, count + 1))
    if set(mapping) != expected:
        raise ValueError(f"provide exactly: {', '.join(f'{n}=PATH' for n in sorted(expected))}")
    return mapping


def run(command):
    print("[run]", " ".join(command))
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Imagesを検証・取り込み・組版・公開準備する")
    parser.add_argument("--id", required=True)
    parser.add_argument("--panel-file", action="append", required=True, metavar="N=PATH",
                        help="生成した各画像を明示的に指定。4回指定する")
    parser.add_argument("--no-compose", action="store_true")
    parser.add_argument("--commit", action="store_true", help="対象YAML・出力・index・stateのみcommit")
    parser.add_argument("--push", action="store_true", help="--commit後にorigin/masterへpush")
    args = parser.parse_args()
    if args.push and not args.commit:
        parser.error("--push requires --commit")
    cfgs = cfglib.load_configs()
    script_path = validate_comic.find_script(args.id)
    script = cfglib.load_script(script_path)
    errors = validate_comic.validate_script(script, cfgs)
    if errors:
        raise SystemExit("\n".join(errors))
    sources = parse_panel_files(args.panel_file, len(script["panels"]))
    panels_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"], "panels")
    os.makedirs(panels_dir, exist_ok=True)
    for number, source in sorted(sources.items()):
        target = os.path.join(panels_dir, f"panel_{number}.png")
        shutil.copy2(source, target)
        print(f"[import] panel {number}: {os.path.basename(source)}")
    if not args.no_compose:
        run([sys.executable, os.path.join(os.path.dirname(__file__), "run_pipeline.py"),
             "--id", script["id"], "--compose"])
        output_errors = validate_comic.validate_output(script, cfgs)
        if output_errors:
            raise SystemExit("\n".join(output_errors))
        print(f"[validate] {script['id']} output: OK")
    if args.commit:
        paths = [script_path, os.path.join(cfglib.OUTPUT_DIR, script["id"]), "index.json", "state/used.json"]
        run(["git", "add", "-A", "--", *paths])
        allowed = {
            os.path.relpath(script_path, cfglib.ROOT).replace("\\", "/"),
            "index.json", "state/used.json",
        }
        output_prefix = f"output/{script['id']}/"
        staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).splitlines()
        unexpected = [path for path in staged if path not in allowed and not path.startswith(output_prefix)]
        if unexpected:
            raise RuntimeError("refusing to commit unrelated staged files: " + ", ".join(unexpected))
        run(["git", "commit", "-m", f"Publish {script['id']} comic"])
        if args.push:
            run(["git", "push", "origin", "master"])


if __name__ == "__main__":
    main()
