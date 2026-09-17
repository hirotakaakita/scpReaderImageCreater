---
name: write-scp-script
description: Create or revise comics/queue/scp-XXX.yaml from the live SCP article while following this repository's comic specification.
---

# Write SCP comic script

Read `AGENTS.md` and `docs/comic-spec.md` first.

## Procedure

1. Determine the requested SCP ID(s). For automatic selection, exclude IDs already in `state/used.json` or `comics/queue/`.
2. Fetch the live article and read the actual Special Containment Procedures and Description. Do not write from memory. Check attribution/author information when available.
3. Decide the panel progression. Default to four panels. Each panel must represent one depictable moment and progress the story/information.
4. Create `comics/queue/scp-XXX.yaml`, following an existing script for serialization shape and `docs/comic-spec.md` for semantics.
5. Use `local_characters` for article-specific people and `config/characters.yaml` for reusable project characters. Keep character keys and scene names stable.
6. Populate captions for the production languages defined in `config/languages.yaml`. Preserve source meaning; do not invent facts to make the strip funnier or more dramatic.
7. Run the repository's script/schema validation when available. Until a dedicated validator exists, load the YAML through the pipeline and use mock verification.
8. Use `$review-scp-script` after the draft is complete. Treat reviewer findings as findings, not truth: verify factual findings against the live article before applying them.

## Quality checklist

- Main-strip facts come from Special Containment Procedures / Description.
- No unsupported causal relationships or events were added.
- Scene and caption agree in every panel.
- Each visible person is declared and uses a stable character name/key.
- Multi-character role assignment is visually unambiguous where needed.
- Shot/composition changes across the strip.
- Captions exist for all production languages.
- Attribution source URL is correct.
- No dialogue bubbles are introduced for the current house style.
- YAML parses successfully.

Do not generate final images as part of this skill.
