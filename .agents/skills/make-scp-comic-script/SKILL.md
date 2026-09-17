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

## Steps

1. Confirm the SCP ID. If choosing automatically, avoid `state/used.json`, `comics/queue/`, and `comics/done/`.
2. Create the mechanical YAML skeleton first when starting a new script:

```bash
python scripts/create_script_stub.py scp-XXX --quiet
```

3. Read the live SCP article. Write from the article, not memory.
4. Fill the YAML in `comics/queue/scp-XXX.yaml`.
   - Description is the default source.
   - Special Containment Procedures may be used only as the final panel payoff.
   - Do not mix addenda/interviews/experiment logs into the main strip.
   - Include per-panel `source` provenance for new scripts.
   - Fill all production-language captions.
5. Do a short internal review: source fidelity, caption/scene mismatch, character keys, and four-panel progression.
6. Validate with compact output:

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source --quiet
```

Use non-strict validation only for legacy scripts that intentionally lack `source`.

## Finish by reporting

- script path
- article URL used
- whether Special Containment Procedures were used
- validation result
- next step: `$generate-scp-comic-images`
