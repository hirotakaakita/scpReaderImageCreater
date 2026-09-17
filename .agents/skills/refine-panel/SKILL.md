---
name: refine-panel
description: Refine one generated comic panel by inspecting externally generated candidates, revising the scene while preserving source facts, and re-importing the accepted image.
---

# Refine generated panel

Read `AGENTS.md`, `docs/comic-spec.md`, the target script, and the panel's `notes` when present.

This repository no longer runs a local image-generation provider. Refinement means:

1. inspect the currently accepted/generated image;
2. revise `scene` or text only when needed;
3. export the updated prompt;
4. generate a new candidate externally;
5. import the accepted candidate with `scripts/accept_external_panel.py`.

## Loop

Use a maximum of six rounds unless the user requests otherwise.

1. Export/update prompts:

```bash
python scripts/run_pipeline.py --id <id> --export-prompts
```

2. Generate the target panel externally using `output/<id>/prompts/panel_<N>.txt`. Follow `$scp-chatgpt-image-handoff`: one square image, one continuous moment, no page/grid/text/borders.
3. Import the candidate if it is worth testing in-context:

```bash
python scripts/accept_external_panel.py --id <id> --panel <N> --source <candidate-image> --provider chatgpt-image
```

4. Inspect the accepted panel and, when useful, the recomposed page. Judge source/caption consistency, character identity/count, role assignment, pose/anatomy, composition, expression, important props, and whether the intended single moment is immediately understandable.
5. If the candidate is acceptable, stop. Do not keep regenerating merely for marginal improvement.
6. If it fails, diagnose common/root causes before editing `scene`.
7. Preserve source facts and any `notes` marked as non-negotiable. Presentation choices may change substantially.
8. After two consecutive rounds of narrow wording patches, stop patching adjectives and reconsider the scene structurally:
   - simplify simultaneous constraints;
   - change shot type/crop;
   - make the action larger and easier to depict;
   - move unstable details out of frame;
   - change spatial arrangement;
   - express the same required fact through a different visible action.
9. Repeat prompt export → external generation → import.

## Caption/text changes

Changing `scene` alone does not require text retranslation. Changing caption/title/addendum meaning does. For semantic text changes, route through `$revise-comic-text` and update all production languages.

## Safety against destructive mock runs

When checking caption layout for a single panel, include `--panel <N> --mock`. Do not run a full-comic mock over uncommitted selected panels: mock generation writes placeholder panel files and can destroy selected images that are not recoverable from Git.

Mock verification is only needed when caption/layout changes.

## Stop conditions

Stop when a usable candidate exists, the round budget is exhausted, the remaining issue requires manual image editing, or the environment cannot perform external image generation/inspection. Report the remaining concrete issue rather than claiming completion.
