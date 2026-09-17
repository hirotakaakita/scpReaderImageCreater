---
name: review-scp-script
description: Independently review one or more SCP comic YAML scripts for source fidelity, scene/caption consistency, character mistakes, and comic progression before rendering.
---

# Review SCP comic script

Read `AGENTS.md` and `docs/comic-spec.md`. Act as a reviewer, not the original writer.

## Inputs

One or more `comics/queue/scp-XXX.yaml` or `comics/done/scp-XXX.yaml` files.

## Procedure

1. Read each target script.
2. Fetch/read the live source article for factual verification when the review concerns source facts. Do not judge source fidelity from model memory.
3. Review panel by panel and then the strip as a whole.
4. Report findings before editing. Each finding should identify the SCP, panel when applicable, severity (`blocking`, `major`, `minor`), category, and concise reason.
5. Categories to check:
   - unsupported or contradicted source fact
   - caption/scene mismatch
   - chronology/context jump
   - character identity/key/order problem
   - multiple actions/moments packed into one still image
   - repeated/weak composition
   - weak progression/payoff
   - addendum/main-description mixing
   - project rule/schema violation
6. Do not manufacture a finding merely to produce feedback. `no findings` is valid.
7. Apply fixes only when the calling task asks for fixes. Before applying a factual fix, verify it against the source article.
8. After fixes, run validation/mock verification where available.

## Review boundary

Image-generation aesthetics that can only be judged from generated images belong to `$refine-panel`, not this source/script review. Translation polish is secondary unless it changes meaning or causes rendering failure.
