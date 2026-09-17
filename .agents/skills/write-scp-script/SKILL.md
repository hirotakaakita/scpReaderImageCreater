---
name: write-scp-script
description: Create or revise comics/queue/scp-XXX.yaml from the live SCP article while following this repository's comic specification.
---

# Write SCP comic script

Read `AGENTS.md` and `docs/comic-spec.md` first.

## Procedure

1. Determine the requested SCP ID(s). For automatic selection, exclude IDs already in `state/used.json` or `comics/queue/`.
2. Fetch the live article and read Description first. Also inspect Special Containment Procedures for context, but **do not normally use it as comic text**. Do not write from memory. Check attribution/author information when available.
3. Build the default four-panel progression from **Description only**: setup → development → reveal/turn → payoff. Prefer four connected Description facts over mixing article sections.
4. Only when Special Containment Procedures provides a particularly effective consequence/response that completes the same story, it may be used in **panel 4 only**. Panels 1–3 must already establish the relevant anomaly from Description, and panel 4 must read as a natural payoff rather than an unrelated procedure.
5. Create `comics/queue/scp-XXX.yaml`, following an existing script for serialization shape and `docs/comic-spec.md` for semantics. For new/revised panels, add `source` provenance when practical (`section`, source `quote`, article `url`, and `fetched_at`).
6. Use `local_characters` for article-specific people and `config/characters.yaml` for reusable project characters. Keep character keys and scene names stable.
7. Populate captions for every production language defined in `config/languages.yaml`. All languages must express the same source fact. Preserve source meaning; do not invent facts to make the strip funnier or more dramatic.
8. Run `python scripts/validate_scripts.py <script>` and mock verification where appropriate.
9. Use `$review-scp-script` after the draft is complete. Treat reviewer findings as findings, not truth: verify factual findings against the live article before applying them.

## Quality checklist

- Panels are Description-only by default.
- If Special Containment Procedures is used, it appears only in panel 4 and completes the same setup established by Description in panels 1–3.
- No Addendum/interview/experiment-log material leaked into the main strip.
- No unsupported causal relationships or events were added.
- Scene and caption agree in every panel.
- Each visible person is declared and uses a stable character name/key.
- Multi-character role assignment is visually unambiguous where needed.
- Shot/composition changes across the strip.
- Captions exist for all production languages and carry the same meaning.
- Attribution source URL is correct.
- No dialogue bubbles are introduced for the current house style.
- YAML parses and validates successfully.

Do not generate final images as part of this skill.
