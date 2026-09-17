---
name: revise-comic-text
description: Revise caption/title/addendum text after human review. Semantic edits update all production languages.
---

# Revise comic text

Use for text-only changes. Do not regenerate artwork unless the new text contradicts the accepted image.

## Request shape

Ask the user to provide or confirm:

```text
対象:
- panel: <1-4 or all>
- field: caption / title / addendum / object_class
- language scope: semantic-all-languages / ja-only typo / en-only wording / other locale-only

修正内容:
- 希望: <how to change it>
- 理由: <why>

制約:
- 画像は再生成しない
- 意味が変わる場合は15言語すべて更新する
```

## Read only

- `AGENTS.md`
- this skill
- target YAML
- live SCP article only if factual meaning changes
- `config/languages.yaml`

Do not read README or unrelated YAML by default.

## Steps

1. Start with compact state when an ID is known:

```bash
python scripts/comic_status.py <id> --json
```

2. Decide language scope. If meaning changes, update every production language. Locale-only typos may touch one language.
3. Keep `source` provenance aligned when caption meaning changes.
4. Validate quietly:

```bash
python scripts/validate_scripts.py <target-yaml> --quiet
```

5. For semantic edits, check that all languages were touched in the git diff:

```bash
python scripts/text_revision_check.py <id-or-yaml-path> --expect semantic-all-languages --panel <N> --field caption
```

6. Recompose/embed all languages without imagegen:

```bash
python scripts/run_pipeline.py --id <id> --skip-generate
python scripts/publish_check.py <id> --json
```

Never use `--languages` as the final run after a semantic edit.

## Finish by reporting

- changed field/panel
- semantic vs locale-only scope
- validation/publish status
- whether any visual check is needed
