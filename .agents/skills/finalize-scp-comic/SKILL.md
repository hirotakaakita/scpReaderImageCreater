---
name: finalize-scp-comic
description: Import generated panel images, normalize them, compose/embed all languages, and run publish checks.
---

# Finalize SCP comic

Use after imagegen produced panel images. Supports full finalize and one-panel replacement.

## Read only

- `AGENTS.md`
- this skill
- target YAML
- `output/<id>/prompts/manifest.json` if present
- `output/<id>/panels/selected.json` for one-panel replacement

Do not read README or unrelated outputs by default.

## Steps

1. Start with compact state:

```bash
python scripts/comic_status.py <id> --json
```

2. Validate target script quietly:

```bash
python scripts/validate_scripts.py comics/queue/<id>.yaml --quiet
```

Use `comics/done/<id>.yaml` if already done.

3. Import images. Choose exactly one input mode:

```bash
python scripts/accept_external_panel.py --id <id> --panel <N> --source <image> --provider imagegen
python scripts/accept_external_panel.py --id <id> --source-dir <dir> --provider imagegen
python scripts/accept_external_panel.py --id <id> --manifest <mapping.json> --provider imagegen
```

For one-panel replacement, import only that panel and confirm the other accepted panels already exist.

4. Compose/embed all production languages:

```bash
python scripts/run_pipeline.py --id <id> --skip-generate
```

Never use `--languages` for the final publication run.

5. Check publication compactly:

```bash
python scripts/publish_check.py <id> --json
python scripts/comic_status.py <id> --quiet
```

Build a review sheet only when useful for visual review:

```bash
python scripts/build_review_sheet.py <id>
```

## Finish by reporting

- imported/replaced panel numbers
- output directory
- publish status
- whether queue moved to done
- any manual visual checks still needed
