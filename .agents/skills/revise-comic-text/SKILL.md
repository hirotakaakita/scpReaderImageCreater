---
name: revise-comic-text
description: Revise comic captions/title/addendum after human review, updating every production language consistently and re-running validation/render checks without regenerating artwork.
---

# Revise comic text after human review

Use this when a human has reviewed an existing comic and asks to change wording, caption meaning, title, object-class presentation, or addendum text while keeping the accepted artwork.

Read `AGENTS.md`, `docs/comic-spec.md`, the target YAML, and `config/languages.yaml` first.

## Non-negotiable multilingual rule

**Never fix only Japanese, only English, or only the language mentioned by the reviewer when the semantic source text changes.** The comic is a 15-language artifact. A semantic edit to a caption/title/addendum must be propagated to **every production language**:

`ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant`

Treat the languages as translations of one canonical meaning. Do not allow old and new meanings to coexist across languages.

If the requested change is purely typographic/localization-specific and intentionally affects one language only (for example a typo in Japanese), preserve the other translations, but still verify that all 15 language entries remain present.

## Procedure

1. Read the human review/request and identify whether it changes **meaning** or only one locale's wording.
2. Re-open the live SCP source when the edit changes factual meaning. Default source is Description. Special Containment Procedures may only supply panel 4 under the project rule in `docs/comic-spec.md`.
3. Update the canonical/source meaning first. If the panel has `source` provenance, keep it aligned with the revised caption.
4. For a semantic change, update all 15 translations in the same edit. Preserve factual equivalence rather than translating old wording mechanically.
5. Do not modify `scene` unless the new caption meaning makes the accepted artwork factually inconsistent. If artwork would need to change, stop and route the visual change through `$refine-panel` instead of silently changing text around a contradictory image.
6. Validate the YAML:

```bash
python scripts/validate_scripts.py <path-to-yaml>
```

7. Recompose/embed using the already selected panels; do **not** regenerate artwork:

```bash
python scripts/run_pipeline.py --id <id> --skip-generate
```

A full-language run is required after semantic text edits so overflow/missing-font checks cover every locale and publication completeness is recalculated.
8. Review warnings. If any language overflows, adjust that language without changing the canonical fact, then rerun the full-language embed.
9. Report which semantic text changed and confirm that all production languages were updated/validated.

## Prohibited shortcuts

- Do not use `--languages ja` or another subset as the final run after a semantic edit.
- Do not leave untranslated/fallback English text in a production locale.
- Do not change the Japanese caption and assume other translations remain valid when meaning changed.
- Do not regenerate selected panel art for text-only corrections.
