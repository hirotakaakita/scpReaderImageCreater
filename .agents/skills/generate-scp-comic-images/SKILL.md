---
name: generate-scp-comic-images
description: Export prompts from an existing SCP comic YAML and generate one image per panel with ChatGPT image generation (`imagegen`). This is the user-facing "画像生成" skill.
---

# Generate SCP comic images with imagegen

Use this when a validated script already exists and the user wants to generate panel art with ChatGPT image generation (`imagegen`).

This skill produces external/generated panel image files. It does **not** finalize the comic unless the user also asks to run `$finalize-scp-comic`.

## Inputs

- `id`: the SCP comic ID, e.g. `scp-173`.
- Optional panel subset, e.g. panel 3 only.
- Optional generation count/reroll instructions.

## Required reading

1. Read `AGENTS.md`.
2. Read `docs/comic-spec.md`.
3. Read the target YAML in `comics/queue/` or `comics/done/`.
4. Read `output/<id>/prompts/manifest.json` after prompt export.

## Procedure

### 1. Validate the script

Run:

```bash
python scripts/validate_scripts.py comics/queue/<id>.yaml
```

If the script is already in `comics/done/`, validate that path instead. Fix script validation errors before image generation.

### 2. Export prompts

Run:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts
```

This writes:

```text
output/<id>/prompts/panel_1.txt
output/<id>/prompts/panel_2.txt
...
output/<id>/prompts/manifest.json
output/<id>/prompts/README.txt
```

The exported prompt is the source of truth for the image request.

### 3. Generate with imagegen, one panel at a time

Use ChatGPT image generation (`imagegen`) once per panel. Do not ask for a page, strip, grid, or multi-panel image.

For each panel, send a request in this shape:

```text
Generate a single image for one SCP comic panel.

Hard requirements:
- Use a square 1:1 canvas.
- Produce exactly one standalone illustration for panel <N>.
- Do not create a comic page, four-panel strip, storyboard, grid, border, or split-screen layout.
- Do not render any text, letters, numbers, captions, signs, labels, sound effects, watermarks, speech bubbles, or thought bubbles.
- Draw one continuous moment only.
- Keep important faces, hands, and props away from the outer edge because the accepted image will be center-cropped/resized to 720x720 if needed.

Use this project prompt exactly as the semantic/art direction:

<contents of output/<id>/prompts/panel_N.txt>
```

Preferred raw save location:

```text
output/<id>/panels_temp/panel_<N>_imagegen_v<M>.png
```

`panels_temp/` is intentionally ignored by git. If the imagegen UI/tool saves elsewhere, keep the returned file path and pass it to `$finalize-scp-comic`.

### 4. Visual acceptance criteria

Before declaring a panel candidate usable, inspect it for:

- square/single-image intent;
- no text or pseudo-text anywhere;
- no speech bubbles/caption boxes/page borders;
- correct number of visible people;
- character identity and role assignment;
- scene/caption/source consistency;
- one clear moment, not multiple actions across time;
- important subject not cropped off;
- adequate blank/uncluttered region where project text will later overlay.

If the issue is just imagegen randomness, rerun the same prompt. If the same problem repeats, edit the YAML `scene` to simplify or clarify the visual moment, then run validation and export prompts again.

### 5. Do not finalize here by default

Do not run `scripts/accept_external_panel.py` or `--skip-generate` unless the user explicitly asks this skill to continue into `$finalize-scp-comic`.

## Completion report

Report:

- prompt export path;
- each generated/accepted raw image path;
- any rejected candidates and why;
- panels still missing;
- next step: `$finalize-scp-comic` with the panel image paths.

## Fallback when imagegen is unavailable

If the current environment cannot call imagegen or cannot save generated files, still export prompts and produce the exact per-panel imagegen request text for the user. Do not pretend images were generated.
