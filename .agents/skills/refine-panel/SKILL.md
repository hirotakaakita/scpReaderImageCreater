---
name: refine-panel
description: Iteratively refine one generated comic panel by inspecting new variants, revising the scene while preserving source facts, and stopping when a usable candidate is found or the round budget is exhausted.
---

# Refine generated panel

Read `AGENTS.md`, `docs/comic-spec.md`, the target script, and the panel's `notes` when present.

This workflow requires local ComfyUI and the ability to inspect generated images. If the current environment cannot run ComfyUI or view the local outputs, do not pretend to complete the visual loop; prepare the scene changes/instructions and leave final generation/selection to the local Codex session or human.

## Loop

Use a maximum of six rounds unless the user requests otherwise.

1. Generate only the target panel's new candidates:

```bash
python scripts/run_pipeline.py --id <id> --panel <N> --variants 4
```

2. Inspect every newly generated candidate as a whole image. Judge source/caption consistency, character identity/count, role assignment, pose/anatomy, composition, expression, important props, and whether the intended single moment is immediately understandable.
3. If at least one candidate is acceptable, stop and identify the best candidate. Do not keep regenerating merely for marginal improvement.
4. If all candidates fail, diagnose common/root causes before editing `scene`.
5. Preserve source facts and any `notes` marked as non-negotiable. Presentation choices may change substantially.
6. After two consecutive rounds of narrow wording patches, stop patching adjectives and reconsider the scene structurally:
   - simplify simultaneous constraints;
   - change shot type/crop;
   - make the action larger and easier to depict;
   - move unstable details out of frame;
   - change spatial arrangement;
   - express the same required fact through a different visible action.
7. Repeat generation.

## Safety against destructive mock runs

When checking caption layout for a single panel, include `--panel <N> --mock`. Do not run a full-comic mock over uncommitted selected panels: mock generation writes placeholder panel files and can destroy selected images that are not recoverable from Git.

Mock verification is only needed when caption/layout changes; changing `scene` alone does not require rechecking text overflow.

## Stop conditions

Stop when a usable candidate exists, the round budget is exhausted, the remaining issue requires manual inpainting, or the environment cannot perform local image generation/inspection. Report the remaining concrete issue rather than claiming completion.
