---
name: scp-chatgpt-image-handoff
description: Prepare an SCP panel for ChatGPT image generation/handoff with a deterministic square canvas and import the returned artwork as an accepted panel.
---

# SCP ChatGPT image handoff

Use this workflow when a panel is generated with ChatGPT image generation or another external image tool.

## Fixed image contract

The handoff image is **always square**. Do not ask for an unconstrained image or infer an aspect ratio from the scene.

- aspect ratio: `1:1`
- accepted target pixels: **720 × 720 px** (the current `config/layout.yaml` panel size)
- one image = one continuous moment
- no text/borders/page layout

If `config/layout.yaml` changes in the future, use its `panel.width` and `panel.height` as the accepted pixel contract and require them to be equal before handoff.

The image-generation request must explicitly say that the result is a square image intended for a 720 × 720 panel. If the image service returns a different pixel size or a non-square asset despite that request, **do not crop from a generated page**. Import the returned single artwork itself with `scripts/accept_external_panel.py`; the script normalizes it with center-crop + high-quality resize to exactly 720 × 720.

## Handoff procedure

1. Export prompts:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts
```

2. Read `output/<id>/prompts/panel_N.txt` for the target panel.
3. Request a single square artwork. Never request a four-panel/page image.
4. Save the raw returned artwork locally.
5. Import the accepted image:

```bash
python scripts/accept_external_panel.py --id <id> --panel <N> --source <returned-image> --provider chatgpt-image
```

6. Repeat for all panels, then run:

```bash
python scripts/run_pipeline.py --id <id> --skip-generate
```

## Thumbnail rule

`thumbnail.png` is generated from accepted `panels/panel_1.png`. Never use or crop `generated-page.png`, `base.png`, or another composed/debug page as the thumbnail source.

`generated-page.png` is not a production artifact. If a handoff client creates it as a preview/debug page, treat it as disposable and do not feed it back into panel or thumbnail generation.
