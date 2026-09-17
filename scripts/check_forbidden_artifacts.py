"""Fail CI when disposable local artifacts are tracked by git."""
import re
import subprocess

FORBIDDEN = [
    re.compile(r"^output/[^/]+/panels_temp/"),
    re.compile(r"^output/[^/]+/prompts/"),
    re.compile(r"^output/[^/]+/generated-page\.png$"),
    re.compile(r"^output/[^/]+/review-sheet\.png$"),
]


def main():
    proc = subprocess.run(["git", "ls-files"], check=True, text=True,
                          stdout=subprocess.PIPE)
    bad = [line for line in proc.stdout.splitlines()
           if any(pattern.search(line) for pattern in FORBIDDEN)]
    if bad:
        print("Forbidden disposable artifacts are tracked:")
        for path in bad:
            print(f"- {path}")
        raise SystemExit(1)
    print("No forbidden disposable artifacts are tracked.")


if __name__ == "__main__":
    main()
