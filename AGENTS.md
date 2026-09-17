# SCP Reader Comic Generator — Codex instructions

## Purpose

This repository generates multilingual SCP comic strips for the SCP Reader app. Codex is the only coding/content agent used for this repository going forward. Do not depend on Claude Code or a Claude subscription.

## Source of truth

- `README.md`: runtime pipeline and local setup.
- `docs/comic-spec.md`: content and comic-generation rules.
- `.agents/skills/`: task-specific Codex workflows.
- `config/*.yaml`: rendering, character, language, and style configuration.
- `comics/queue/*.yaml`: scripts waiting to be rendered.
- `comics/done/*.yaml`: completed scripts.
- `output/<id>/meta.json`: generated artifact metadata.
- `state/used.json`: legacy/current duplicate-generation guard. Do not delete it until state management is deliberately migrated.

If an old `.claude/` file conflicts with `AGENTS.md`, `docs/`, or `.agents/skills/`, follow the Codex files. `.claude/` is retained temporarily only as migration reference and should not be treated as active instructions.

## Standing content rules

- Fetch and read the live SCP article before writing or materially changing a comic script. Do not rely on model memory or summaries.
- Base the main comic on Special Containment Procedures / Description. Do not mix Addendum, interview logs, or experiment logs into the main strip unless the task explicitly calls for a separate treatment.
- Do not imitate official SCP attachment images. Use textual article descriptions as the visual source.
- Do not invent named/canon characters. Article-specific people belong in `local_characters`; reusable characters must come from `config/characters.yaml`.
- `scene` describes the image and is written in English. It must remain consistent with the corresponding caption/source facts.
- Do not generate dialogue bubbles for the current house style. Text is composited by Python after image generation.
- Keep character keys/names stable across panels. For multi-character scenes, keep `characters` ordering aligned with the order in which their actions are described in `scene`.
- Vary shot type/composition across panels rather than repeating the same framing.
- Preserve attribution and CC BY-SA requirements.

## Engineering rules

- Prefer deterministic Python validation over asking Codex to remember mechanical constraints.
- Treat YAML scripts as an interface between the agent workflow and the Python pipeline. New rules that can be machine-validated should become validators/tests.
- Never mark an artifact publish-complete from an unknown/`None` state. Publishability must be positively established.
- Do not overwrite selected panel images when generating variants.
- Do not run multiple ComfyUI comic generations in parallel; GPU/RAM pressure and queue contention have caused failures.
- Mock output is disposable and must not be committed as production output.
- Keep provider-specific image-generation behavior behind `scripts/providers/`.

## Codex workflows

Use the repository skills when applicable:

- `$write-scp-script`: create or revise an SCP comic script.
- `$review-scp-script`: independently review script/source consistency and comic structure.
- `$prepare-scp-comic`: take scripts through review, mock verification, and prompt export without generating final images.
- `$refine-panel`: refine a problematic generated panel while preserving source facts.

Writer and reviewer are separate roles even though both are performed by Codex. A review should first report findings; fixes are applied only after the findings are checked against the source article.

## Verification

For Python changes, run the smallest relevant tests first, then the broader suite when available. For pipeline/rendering changes, use mock generation where appropriate so verification does not require ComfyUI.

Do not claim a command or test passed unless it was actually run. If the environment cannot run it, report that explicitly.

## Migration note

The repository is being migrated from Claude-oriented instructions to Codex. Do not add new instructions under `.claude/`. New reusable procedures belong under `.agents/skills/`; always-on rules belong here; detailed stable specifications belong under `docs/`.
