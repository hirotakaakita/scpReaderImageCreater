---
name: scp-chatgpt-image-handoff
description: Prepare an SCP panel for ChatGPT image generation/handoff with a deterministic square canvas and save/normalize the returned artwork as an accepted panel candidate.
---

# SCP ChatGPT image handoff

Use this workflow when a panel is generated outside the local ComfyUI provider via ChatGPT image generation.

## Fixed image contract

The handoff image is **always square**. Do not ask for an unconstrained image or infer an aspect ratio from the scene.

- aspect ratio: `1:1`
- handoff target pixels: **720 × 720 px** (the current `config/layout.yaml` accepted panel size)
- one image = one continuous moment
- no text/borders/page layout

If `config/layout.yaml` changes in the future, use its `panel.width` and `panel.height` as the accepted pixel contract and require them to be equal before handoff.

The image-generation request must explicitly say that the result is a square image intended for a 720 × 720 panel. If the image service returns a different pixel size or a non-square asset despite that request, **do not crop from a generated page**. Normalize the returned single artwork itself with center-crop + high-quality resize to exactly 720 × 720 before accepting it.

## Handoff procedure

1. Read the target YAML panel and build/use the same semantic prompt constraints as the normal generator: scene, character definitions, caption/source context, empty text-overlay area, composition rules, and zero-text rule.
2. Request a single square artwork. Never request a four-panel/page image.
3. Save the raw returned artwork as a candidate, preserving it for provenance when practical.
4. Normalize the candidate to exactly the configured accepted panel pixels.
5. Put only the normalized single artwork at `output/<id>/panels/panel_N.png` when it is accepted.
6. Record provider/source dimensions and accepted dimensions in selection/generation metadata.
7. Run `--skip-generate` to compose/embed after all accepted panels are ready.

## Thumbnail rule

`thumbnail.png` is generated from accepted `panels/panel_1.png`. Never use or crop `generated-page.png`, `base.png`, or another composed/debug page as the thumbnail source.

`generated-page.png` is not a production artifact in the current pipeline. If a ChatGPT handoff client creates it as a preview/debug page, treat it as disposable and do not feed it back into panel or thumbnail generation.
