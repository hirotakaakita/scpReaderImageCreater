---
name: generate-scp-comic-images
description: Export imagegen requests and generate full-comic or one-panel image candidates. Stops before final compose unless asked.
---

# Generate SCP comic images

Use for: full image generation or one-panel regeneration with ChatGPT image generation (`imagegen`).

## Read only

- `AGENTS.md`
- this skill
- target YAML
- `output/<id>/panels/selected.json` only for regeneration
- `output/<id>/prompts/manifest.json` after export

Do not read README or unrelated YAML by default.

## Steps

1. Start with compact state:

```bash
python scripts/comic_status.py <id> --json
```

2. Resolve target:
   - no panel specified: all panels
   - `panel N` / `Nコマ目だけ`: only that panel
3. Validate target script quietly:

```bash
python scripts/validate_scripts.py comics/queue/<id>.yaml --quiet
```

Use `comics/done/<id>.yaml` if the script is already done.

4. Export ready-to-copy imagegen request files:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts
python scripts/run_pipeline.py --id <id> --export-prompts --panel <N>
```

Use `output/<id>/prompts/panel_N_imagegen_request.txt` for imagegen. Do not manually assemble prompts from README unless debugging.

5. Generate one image per target panel. Hard rule: one square standalone illustration only; no page/grid/strip/frame/border/text/caption/bubbles.
6. For repeated failure on one panel, edit only that panel's `scene`, preserve caption/source facts, revalidate, and re-export only that panel.

## Finish by reporting

- mode: all panels or panel N only
- exported `panel_N_imagegen_request.txt` paths
- generated raw image paths
- rejected candidates, if any
- next step: `$finalize-scp-comic`
