---
name: review-scp-script
description: Independently review one or more SCP comic YAML scripts for source fidelity, scene/caption consistency, character mistakes, source-section policy, and comic progression before rendering.
---

# Review SCP comic script

Read `AGENTS.md` and `docs/comic-spec.md`. Act as a reviewer, not the original writer.

## Procedure

1. Read each target script and fetch/read the live source article for factual verification. Do not judge source fidelity from model memory.
2. Check source-section policy first: panels should use Description by default. Special Containment Procedures is acceptable only in the final panel, only when it naturally completes the Description-based setup from earlier panels. Addenda/interviews/experiment logs do not belong in the normal main strip.
3. Review panel by panel and then the strip as a whole.
4. Report findings before editing. Each finding should identify SCP, panel when applicable, severity (`blocking`, `major`, `minor`), category, and concise reason.
5. Categories to check:
   - wrong source section / containment procedure used before final panel
   - unsupported or contradicted source fact
   - caption/scene mismatch
   - chronology/context jump
   - character identity/key/order problem
   - multiple actions/moments packed into one still image
   - repeated/weak composition
   - weak progression/payoff
   - supplementary-material mixing
   - project rule/schema violation
6. Do not manufacture a finding merely to produce feedback. `no findings` is valid.
7. Apply fixes only when the calling task asks for fixes. Before applying a factual fix, verify it against the source article. If caption meaning changes, use the `$revise-comic-text` rule: update all production languages, not only ja/en.
8. After fixes, run validation/mock verification where available.

Image-generation aesthetics that can only be judged from generated images belong to `$refine-panel`, not this source/script review.
