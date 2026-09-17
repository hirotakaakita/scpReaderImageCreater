# SCP Reader Comic Generator — Codex instructions

## Purpose

This repository generates multilingual SCP comic strips for the SCP Reader app. Codex is the only coding/content agent used for this repository. Do not depend on Claude Code or a Claude subscription.

The repository does **not** contain or call a local image-generation provider. Codex/Python exports prompts, image generation is done with ChatGPT image generation (`imagegen`) or another external tool, and Python accepts/normalizes those images, composes the comic, embeds multilingual text, and runs deterministic publication checks.

## Source of truth

- `README.md`: runtime pipeline, request templates, and local setup.
- `docs/comic-spec.md`: content and comic-generation rules.
- `.agents/skills/`: user-facing Codex workflows.
- `config/*.yaml`: rendering, character, language, and prompt configuration.
- `comics/queue/*.yaml`: scripts waiting to be rendered.
- `comics/done/*.yaml`: completed scripts.
- `output/<id>/meta.json`: generated artifact metadata.
- `state/used.json`: duplicate-generation guard. Do not delete it without an explicit state migration.

Do not add Claude-specific instruction files. New reusable procedures belong under `.agents/skills/`; always-on rules belong here; stable model-independent specifications belong under `docs/`.

## Standing content rules

- Fetch and read the live SCP article before writing or materially changing a comic script. Do not rely on model memory or summaries.
- **Use Description as the default source for the four-panel comic.** Do not normally use Special Containment Procedures as caption/scene material.
- If Special Containment Procedures is exceptionally useful to complete the same story, it may appear **only in panel 4**, as the consequence/response to Description-based panels 1–3. The transition must preserve a coherent setup → development → turn → payoff.
- Do not mix Addendum, interview logs, experiment logs, or other supplementary material into the main strip unless the task explicitly calls for a separate treatment.
- Do not imitate official SCP attachment images. Use textual article descriptions as the visual source.
- Do not invent named/canon characters. Article-specific people belong in `local_characters`; reusable characters must come from `config/characters.yaml`.
- `scene` describes the image and is written in English. It must remain consistent with the corresponding caption/source facts.
- Do not generate dialogue bubbles for the current house style. Text is composited by Python after image generation.
- Keep character keys/names stable across panels. For multi-character scenes, keep `characters` ordering aligned with the order in which their actions are described in `scene`.
- Vary shot type/composition across panels rather than repeating the same framing.
- Preserve attribution and CC BY-SA requirements.
- **A semantic text edit after human review must be propagated to all production languages.** Never leave different factual meanings between ja/en/other locales. Use `$revise-comic-text` and `scripts/text_revision_check.py`.

## Engineering rules

- Prefer deterministic Python validation over asking Codex to remember mechanical constraints.
- Treat YAML scripts as an interface between the agent workflow and the Python pipeline. New mechanical rules should become validators/tests.
- Prefer `python scripts/validate_scripts.py <script> --strict-source` for new scripts. Plain `--all` remains backward-compatible for existing queued scripts.
- Use `python scripts/comic_status.py <id>` before resuming a partially completed comic or debugging a failed publish.
- Never mark an artifact publish-complete from an unknown/`None` state. Publishability must be positively established.
- A partial-language render is not a publication run. Run all production languages successfully before publishing.
- Do not add local image provider implementations back into `scripts/providers/` without an explicit design decision.
- Real image generation is external. The normal flow is `--export-prompts` → imagegen → `scripts/accept_external_panel.py` → `--skip-generate`.
- `--export-prompts` writes ready-to-copy `panel_N_imagegen_request.txt` files. Prefer those over hand-assembling prompts.
- Generate one image per panel. Do not ask imagegen for a page, grid, strip, storyboard, or multi-panel result.
- One bad panel should be regenerated as one panel. Use `python scripts/run_pipeline.py --id <id> --export-prompts --panel <N>` and keep other accepted panels unchanged.
- `--variants` is mock-only. Do not use it for real generation.
- Accepted panel assets and thumbnails are square and normalized to `config/layout.yaml`'s panel/thumbnail pixel dimensions.
- `thumbnail.png` must be derived from accepted `panels/panel_1.png`, never cropped from a composed page/debug page such as `base.png` or `generated-page.png`.
- `output/<id>/panels_temp/`, `output/<id>/prompts/`, `output/<id>/generated-page.png`, and `output/<id>/review-sheet.png` are disposable and must not be committed. CI rejects these artifacts.

## User-facing Codex workflows

Use these skills as the public entry points. Older low-level skills were intentionally folded into these.

- `$make-scp-comic-script`: **台本作成**. Read the live article, create/revise YAML, run an internal review pass, and validate.
- `$generate-scp-comic-images`: **画像生成**. Export prompts and generate one image per target panel with ChatGPT image generation (`imagegen`), including one-panel regeneration.
- `$finalize-scp-comic`: **生成済み画像取り込み漫画完成**. Import generated images individually, from a directory, or from a manifest; normalize accepted panels; compose/embed all languages; build a review sheet; and run publish checks. It can import all panels or replace one regenerated panel.
- `$revise-comic-text`: Human-review text corrections across all production languages without regenerating accepted artwork. Ask for/parse target panel, field, language scope, desired wording, and whether meaning changes.

Typical user requests should map as follows:

- "scp-XXX の漫画台本を作って" → `$make-scp-comic-script`
- "scp-XXX の画像を生成して" → `$generate-scp-comic-images`
- "scp-XXX の3コマ目だけ再生成して" → `$generate-scp-comic-images` with `--panel 3`, then `$finalize-scp-comic` for panel 3 if the image is accepted
- "この画像で漫画を完成させて" → `$finalize-scp-comic`
- "panel 2のcaptionをこう直して" → `$revise-comic-text`

## Verification

For Python changes run the smallest relevant tests first, then `pytest -q`. Validate scripts with `python scripts/validate_scripts.py --all` when script/schema rules change. Use `python scripts/check_forbidden_artifacts.py` before committing production output. For pipeline/rendering changes use mock generation where appropriate.

Do not claim a command or test passed unless it was actually run. If the environment cannot run it, report that explicitly.
