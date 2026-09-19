---
name: make-scp-comic-script
description: Create or revise one SCP comic script YAML from the live SCP article. Stops before image generation.
---

# Make SCP comic script

Use for: `scp-XXX の漫画台本を作って`, `台本を作って`, `N本分の台本を作って`.

## Read only

- `AGENTS.md`
- `docs/comic-spec.md`
- target live SCP article
- `config/languages.yaml`
- `config/characters.yaml` only if choosing reusable characters
- existing target YAML only when revising

Do not read README or unrelated SCP YAML unless the user asks.

## Script style

Prefer a **source-faithful explanatory SCP comic** over a punchline-driven 4-koma.

The goal is to break the original SCP article into four visual explanation beats. Captions should help the reader understand the SCP from the original text. Do not compress the source into vague one-line summaries just to make it feel more like a gag comic.

Default beat structure:

1. appearance / identity / scale
2. internal structure / anomalous space / observed behavior
3. material / mechanism / important detail
4. consequence / test result / procedural caution

Keep concrete source facts whenever possible:

- measurements and quantities;
- physical form and structure;
- internal/external contradictions;
- biological or physical composition;
- anomalous effects;
- relevant procedural cautions.

Description is the primary source. If Description alone can fill four panels, do not use other sections. Special Containment Procedures may be used only when needed for explanatory value, normally as panel 4, and must connect naturally from panels 1-3.

Avoid:

- punchline-first rewriting;
- over-short captions that lose important source facts;
- unsupported interpretation or causal links;
- Addendum/interview/experiment-log material unless the user explicitly asks.

## Steps

1. Confirm the SCP ID. If choosing automatically, avoid `state/used.json`, `comics/queue/`, and `comics/done/`.
2. Create the mechanical YAML skeleton first when starting a new script:

```bash
python scripts/create_script_stub.py scp-XXX --quiet
```

3. Read the live SCP article. Write from the article, not memory.
4. Fill the YAML in `comics/queue/scp-XXX.yaml`.
   - Use source-backed explanatory captions, not vague summaries.
   - Description is the default source.
   - Special Containment Procedures may be used only as the final-panel explanatory payoff.
   - Include per-panel `source` provenance for new scripts.
   - Fill all production-language captions with the same meaning.
5. Do a short internal review:
   - source.quote important facts preserved in caption;
   - caption/scene consistency;
   - Description-first policy;
   - character keys;
   - four-panel explanatory progression.
6. Validate with compact output:

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source --quiet
```

Use non-strict validation only for legacy scripts that intentionally lack `source`.

## Finish by reporting

- script path
- article URL used
- whether Special Containment Procedures were used, and why
- validation result
- next step: `$generate-scp-comic-images`
