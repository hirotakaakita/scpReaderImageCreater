---
name: prepare-scp-comic
description: Prepare one or more SCP comics from Description-first script writing through independent review, mock verification, and prompt export without running final image generation.
---

# Prepare SCP comic

Read `AGENTS.md` and `docs/comic-spec.md`.

For each requested SCP:

1. Use `$write-scp-script` to create/revise the script from the live article. Build from Description by default. Special Containment Procedures may be used only in the final panel when it naturally completes the Description-based first three panels.
2. Use `$review-scp-script` as an independent review pass. Verify factual findings against the article and apply justified fixes. Any semantic caption fix must update all production languages.
3. Run mock verification:

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

Resolve text overflow/schema/runtime errors. Mock artifacts are disposable and must not replace committed production artifacts.

4. Export generation prompts:

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

5. Report script/review/validation status and prompt export location.

This skill does not run final ComfyUI generation and does not select visual variants.

After preparation:

```bash
python scripts/run_pipeline.py --id scp-XXX --variants 4
python scripts/select_variant.py --id scp-XXX --panel 1 --variant <M>
# repeat selection for all panels
python scripts/run_pipeline.py --id scp-XXX --skip-generate
```

Do not parallelize multiple ComfyUI comic generations.
