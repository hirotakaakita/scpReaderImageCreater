---
name: prepare-scp-comic
description: Prepare one or more SCP comics from script writing through independent review, mock verification, and ComfyUI prompt export without running final image generation.
---

# Prepare SCP comic

Read `AGENTS.md` and `docs/comic-spec.md`.

For each requested SCP:

1. Use `$write-scp-script` to create/revise the script from the live article.
2. Use `$review-scp-script` as an independent review pass. Verify factual findings against the article and apply justified fixes.
3. Run mock verification:

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

Resolve text overflow/schema/runtime errors. Mock artifacts are disposable and must not replace committed production artifacts.

4. Export generation prompts:

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

5. Report the script/review/validation status and the prompt export location.

This skill does not run final ComfyUI generation and does not select visual variants.

## After preparation

Final local image work remains:

```bash
python scripts/run_pipeline.py --id scp-XXX --variants 4
# human selects each accepted candidate into output/scp-XXX/panels/panel_N.png
python scripts/run_pipeline.py --id scp-XXX --skip-generate
```

Do not parallelize multiple ComfyUI comic generations.
