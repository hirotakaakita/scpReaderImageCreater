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
- `config/style.yaml` when adjusting or checking art direction
- `config/style_references/approved_published_style.png` for the fixed, user-approved single-image style reference
- `config/style_references/published_scp105_base.png` only when the original published reference is needed
- `output/<id>/panels/selected.json` only for regeneration
- `output/<id>/prompts/manifest.json` after export

Do not read README or unrelated YAML by default.

## People in scenes

Choose whether to include people based on the explanatory composition; neither require nor exclude them by default. Do not add or strengthen blanket `No people` instructions in the name of source fidelity. Reserve an explicit people-free constraint for a user request or a scene-specific need. Supporting figures observing or examining the subject are allowed, but must not introduce unsupported anomalous effects or causal claims. The presence of a person alone is not a reason to reject a candidate unless it conflicts with such a justified constraint.

## Visual style

This house style is fixed by explicit user approval. For all future SCP image generation, inspect and pass `config/style_references/approved_published_style.png` to imagegen as the primary rendering reference. It is a preserved copy of the approved `output/scp-105/raw/published_style/panel_4_v1.png`. Transfer rendering technique only, not these characters, clothing, props or composition to unrelated SCPs. Keep shot and pose variety. Do not switch styles, substitute a newer candidate, or overwrite this reference unless the user explicitly requests a style change. Use ChatGPT imagegen, not a LoRA-based local renderer.

Use the actual user-designated published SCP-105 images as the visual authority, not a date-based inference from an old generation configuration. The local reference `config/style_references/published_scp105_base.png` is a copy of `../scpjpReaderActions/manga/scp-105/base.png`. It shows delicate manga-influenced faces, soft dimensional painted shading, fine loose hair strands, realistic clothing and worn concrete/metal, and dark low-saturation gray-brown cinematic surroundings. Faces remain illustrated rather than photographic, with expressive but not oversized eyes and restrained contours.

Inspect the reference before generation. It is a composed page used ONLY for rendering technique: never reproduce its page layout, borders, text areas, anomalous effects, poses or identities unless independently required by the target scene. Generate one square standalone scene. The old September 10 LoRA configuration does not establish the provenance or desired appearance of these published images. Do not use the monochrome lithograph approximation or the later F variant as the default reference.

Keep the SCP or relevant detail readable at roughly 360 px wide through motivated local light, focal midtones and restrained color contrast. Preserve source-described colors, ages, anatomy and identities; do not invent glow. Avoid crushed blacks, uniformly bright scenes, flat cel-only shading, exaggerated cartoon eyes, heavy ink outlines and cream paper backgrounds.

Keep `config/style.yaml` synchronized. Re-export after style changes, preserving scene facts, captions, provenance and composition directions. Prior panels may establish identity, but must not override this rendering reference.

## Composition and pose variety

Before export, compare all four target `scene` descriptions for repeated shot distance, camera angle, subject placement, and human posture/action. Make each scene's staging explicit and favor meaningful changes between adjacent panels. Avoid a fixed camera sequence across every SCP. If the scenes are near-duplicates without an explanatory reason, refine their visual staging before validation/export, preserving caption and source facts. Do not invent anomalous behavior or move a source-described immobile subject to achieve variety; intentional comparisons may keep the same framing and pose.

Treat previous-panel references as identity, clothing, material, and rendering references, not composition or pose templates. Explicitly tell imagegen to follow the current scene's camera, blocking, action, and gaze instead of copying the reference arrangement. Preserve identity only for characters actually recurring in the story; an incidental observer need not become every panel's protagonist. For a localized correction of an otherwise good candidate, preserve its approved composition instead.

Review the generated set for accidental repetition as well as individual quality. If a panel copies another panel's composition or pose despite a distinct scene, regenerate only that panel with concrete staging corrections, not a vague request for more variety. Do not reject repetition that is necessary for source fidelity or explanatory clarity.

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

These request files are internal intermediate artifacts, not a human review gate. If image generation is requested, continue directly from export to imagegen without waiting for prompt approval or presenting full prompts. For a combined script-and-images request, finish all requested panels before reporting results. Stop at export only when the user explicitly requests preparation/export only. Import and final composition remain separate unless requested.

5. Generate one image per target panel. Hard rule: one square standalone illustration only; no page/grid/strip/frame/border/text/caption/bubbles.
6. For repeated failure on one panel, edit only that panel's `scene`, preserve caption/source facts, revalidate, and re-export only that panel.

## Finish by reporting

- mode: all panels or panel N only
- exported `panel_N_imagegen_request.txt` paths
- generated raw image paths
- rejected candidates, if any
- next step: `$finalize-scp-comic`
