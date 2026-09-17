---
name: prepare-scp-comic
description: Prepare one or more SCP comics from Description-first script writing through independent review, mock verification, and external image prompt export without running image generation.
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

4. Export external image-generation prompts:

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

This writes `output/scp-XXX/prompts/panel_N.txt`, reference images when available, and a handoff manifest. It does **not** call any local image provider.

5. Report script/review/validation status and prompt export location.

## After preparation

Generate each panel image outside the repository, for example via ChatGPT image generation following `$scp-chatgpt-image-handoff`. Then import each accepted image:

```bash
python scripts/accept_external_panel.py --id scp-XXX --panel 1 --source <panel-1-image> --provider chatgpt-image
# repeat for all panels
python scripts/run_pipeline.py --id scp-XXX --skip-generate
```

`--variants` is mock-only and must not be used for real image generation.
