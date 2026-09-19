# SCP Reader Comic Generator — Codex instructions

## Scope

Codex is the only agent used for this repository. There is no local image-generation provider. Images are generated externally with ChatGPT image generation (`imagegen`) or another external tool, then imported by Python.

Keep this file small. `README.md` is human-facing and long; do **not** read it by default. Read it only when the user asks for usage/templates or a skill explicitly needs a human-facing command example.

## Token-saving default

When an SCP ID is known, start with:

```bash
python scripts/comic_status.py <id> --json
```

Then read only the minimum files needed for the current task:

- this `AGENTS.md`;
- exactly one relevant `.agents/skills/*/SKILL.md`;
- the target `comics/queue/<id>.yaml` or `comics/done/<id>.yaml`;
- relevant `output/<id>/` metadata such as `prompts/manifest.json`, `panels/selected.json`, or `meta.json`.

Do not read README, all YAML scripts, all output directories, or the whole repository unless the user explicitly requests broad review. Prefer `--json`, `--quiet`, and targeted commands over verbose logs.

## Core rules

- Fetch/read the live SCP article before writing or materially changing a script.
- Write source-faithful explanatory SCP comics, not punchline-first 4-koma. Captions should preserve important concrete facts from the source text.
- Use Description as the default source for the four-panel comic.
- Special Containment Procedures are exceptional: final panel only, and only when they naturally complete panels 1-3.
- Do not mix addenda/interviews/experiment logs into the normal main strip.
- Do not imitate official SCP attachment images; visualize textual descriptions only.
- No dialogue bubbles for the current house style. Python overlays all text later.
- Semantic text edits must update all production languages. Locale-only typo fixes may touch one language.
- Generate one image per panel. Never ask imagegen for a page, grid, strip, storyboard, frame, border, speech bubbles, or text.
- One bad panel should be regenerated/replaced as one panel; keep other accepted panels unchanged.
- Publishability is fail-closed: only explicit `complete: true` plus `publish_check` success is publishable.

## User-facing skills

Use these four public entry points:

- `$make-scp-comic-script`: create/revise a script YAML from the live article. Prefer `scripts/create_script_stub.py` before filling content.
- `$generate-scp-comic-images`: export imagegen prompts and generate full-comic or one-panel image candidates.
- `$finalize-scp-comic`: import generated images, normalize accepted panels, compose/embed all languages, and run publish checks.
- `$revise-comic-text`: revise caption/title/addendum text after human review.

## Commands

Use targeted commands first:

```bash
python scripts/comic_status.py <id> --json
python scripts/create_script_stub.py <id> --json
python scripts/validate_scripts.py comics/queue/<id>.yaml --strict-source --quiet
python scripts/run_pipeline.py --id <id> --export-prompts [--panel N]
python scripts/accept_external_panel.py --id <id> --panel N --source <image> --provider imagegen
python scripts/run_pipeline.py --id <id> --skip-generate
python scripts/publish_check.py <id> --json
```

Use `python scripts/validate_scripts.py --all` only for CI, schema-wide changes, or final broad verification.

## Reporting

Be concise. Report commands actually run, pass/fail status, files changed, and the next action. Do not claim tests passed unless they ran.
