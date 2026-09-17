---
name: generate-scp-comic-images
description: Export prompts from an existing SCP comic YAML and generate full-comic or single-panel art with ChatGPT image generation (`imagegen`). This is the user-facing "画像生成" skill.
---

# Generate SCP comic images with imagegen

Use this when a validated script already exists and the user wants to generate panel art with ChatGPT image generation (`imagegen`).

This skill can run in two modes:

- **Full image generation**: generate one image for every panel.
- **Single-panel regeneration**: regenerate only one specified panel, leaving other accepted panels unchanged.

It does **not** finalize the comic unless the user also asks to run `$finalize-scp-comic`.

## Inputs

- `id`: the SCP comic ID, e.g. `scp-173`.
- Optional `panel`: one-based panel number. When present, generate/regenerate only that panel.
- Optional reroll count or acceptance criteria from the user.
- Optional reason for regeneration, e.g. "panel 3 has text", "character count is wrong", "crop is bad", "make the emotion stronger".

## Required reading

1. Read `AGENTS.md`.
2. Read `docs/comic-spec.md`.
3. Read the target YAML in `comics/queue/` or `comics/done/`.
4. If this is regeneration, inspect existing `output/<id>/panels/selected.json` and the current accepted panel image when available.
5. Read `output/<id>/prompts/manifest.json` after prompt export.

## Procedure

### 1. Resolve mode

Decide from the user request:

- No panel specified: full image generation for all panels.
- `panel N`, `Nコマ目だけ`, `panel_Nだけ`, or a problem localized to one panel: single-panel regeneration.

For single-panel regeneration, do not touch other panel prompts/images unless the user explicitly asks.

### 2. Validate the script

Run:

```bash
python scripts/validate_scripts.py comics/queue/<id>.yaml
```

If the script is already in `comics/done/`, validate that path instead. Fix script validation errors before image generation.

### 3. Export prompts

Full export:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts
```

Single-panel export/regeneration:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts --panel <N>
```

Single-panel export writes/updates only `output/<id>/prompts/panel_<N>.txt` and a partial manifest for that run. The exported prompt is the source of truth for the image request.

### 4. Generate with imagegen, one panel at a time

Use ChatGPT image generation (`imagegen`) once per target panel. Do not ask for a page, strip, grid, or multi-panel image.

For each target panel, send a request in this shape:

```text
Generate a single image for one SCP comic panel.

Hard requirements:
- Use a square 1:1 canvas.
- Produce exactly one standalone illustration for panel <N>.
- Do not create a comic page, four-panel strip, storyboard, grid, border, frame, or split-screen layout.
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

### 5. Single-panel regeneration loop

When regenerating one panel:

1. State the current issue in concrete visual terms.
2. Try the existing exported prompt once if the issue looks random.
3. If the same issue repeats, modify only that panel's `scene` in the YAML while preserving its caption/source facts.
4. Run validation again.
5. Re-export only that panel:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts --panel <N>
```

6. Generate only that panel with imagegen.
7. If the user wants to accept it immediately, continue with `$finalize-scp-comic` for that single panel path. Otherwise report the candidate path and wait for selection.

Do not regenerate all panels to fix a single bad panel.

### 6. Visual acceptance criteria

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

## Completion report

Report:

- mode: full generation or single-panel regeneration;
- prompt export path(s);
- each generated/accepted raw image path;
- any rejected candidates and why;
- panels still missing;
- next step: `$finalize-scp-comic` with the target panel image paths.

## Fallback when imagegen is unavailable

If the current environment cannot call imagegen or cannot save generated files, still export prompts and produce the exact per-panel imagegen request text for the user. Do not pretend images were generated.
