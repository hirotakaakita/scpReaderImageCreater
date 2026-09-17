---
name: revise-comic-text
description: Revise comic captions/title/addendum after human review, updating every production language consistently and re-running validation/render checks without regenerating artwork.
---

# Revise comic text after human review

Use this when a human has reviewed an existing comic and asks to change wording, caption meaning, title, object-class presentation, or addendum text while keeping the accepted artwork.

Read `AGENTS.md`, `docs/comic-spec.md`, the target YAML, and `config/languages.yaml` first.

## How users should request text fixes

Encourage requests in this shape. The user does not need to fill every field, but you must infer/clarify the missing parts before editing.

```text
$revise-comic-text で scp-XXX のテキストを修正してください。

対象:
- panel: <1-4 or all>
- field: caption / title / addendum / object_class
- language scope: semantic-all-languages / ja-only typo / en-only wording / other locale-only

修正内容:
- 現在: <任意。分かる範囲で>
- 希望: <どう直したいか>
- 理由: <分かりにくい、原文と違う、長すぎる、語調を変えたい、など>

制約:
- 画像は再生成しない
- 意味が変わる場合は15言語すべて更新する
```

Common valid requests:

```text
$revise-comic-text で scp-173 の panel 4 caption を、オチが分かりやすいように短くしてください。意味が変わるので15言語すべて更新してください。
```

```text
$revise-comic-text で scp-173 の日本語タイトルだけ誤字修正してください。意味は変えません。
```

```text
$revise-comic-text で scp-173 の addendum を削除/追加してください。追加する場合は15言語すべて作ってください。
```

If a request says only "ここの文章を直して" but does not identify the panel/field, ask which panel/field before editing unless the target is obvious from the conversation.

## Non-negotiable multilingual rule

**Never fix only Japanese, only English, or only the language mentioned by the reviewer when the semantic source text changes.** The comic is a 15-language artifact. A semantic edit to a caption/title/addendum must be propagated to every production language:

`ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant`

Treat the languages as translations of one canonical meaning. Do not allow old and new meanings to coexist across languages.

If the requested change is purely typographic/localization-specific and intentionally affects one language only, preserve the other translations, but still verify that all 15 language entries remain present.

## Procedure

1. Parse the request into target panel/field, requested meaning, and language scope.
2. Decide whether it changes meaning or only one locale's wording. If unclear, ask a clarifying question before editing.
3. Re-open the live SCP source when the edit changes factual meaning. Default source is Description. Special Containment Procedures may only supply panel 4 under the project rule in `docs/comic-spec.md`.
4. Update the canonical/source meaning first. If the panel has `source` provenance, keep it aligned with the revised caption.
5. For a semantic change, update all 15 translations in the same edit. Preserve factual equivalence rather than translating old wording mechanically.
6. Do not modify `scene` unless the new caption meaning makes the accepted artwork factually inconsistent. If artwork would need to change, stop and route the visual change through `$generate-scp-comic-images` for the affected panel and then `$finalize-scp-comic`.
7. Validate the YAML:

```bash
python scripts/validate_scripts.py <path-to-yaml>
```

8. Recompose/embed using the already accepted panels; do **not** run imagegen for text-only corrections:

```bash
python scripts/run_pipeline.py --id <id> --skip-generate
```

A full-language run is required after semantic text edits so overflow/missing-font checks cover every locale and publication completeness is recalculated.

9. Run the publish gate:

```bash
python scripts/publish_check.py <id>
```

10. Review warnings. If any language overflows, adjust that language without changing the canonical fact, then rerun the full-language embed and publish check.
11. Report which semantic text changed and confirm that all production languages were updated/validated.

## Prohibited shortcuts

- Do not use `--languages ja` or another subset as the final run after a semantic edit.
- Do not leave untranslated/fallback English text in a production locale.
- Do not change the Japanese caption and assume other translations remain valid when meaning changed.
- Do not regenerate selected panel art for text-only corrections.
