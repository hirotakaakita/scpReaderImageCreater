---
name: make-scp-comic-script
description: Create an SCP comic script from a live SCP article, review it, and validate the YAML. This is the user-facing "台本作成" skill.
---

# Make SCP comic script

Use this when the user asks to create an SCP comic/script, for example: "scp-173 の漫画を作って", "台本を作って", or "N本分の台本を作って".

This skill stops at a validated YAML script. It does **not** generate images.

## Inputs

- One SCP ID such as `scp-173`, or a list of IDs.
- Optional panel count. Default is 4.
- Optional tone/constraints from the user.

## Required reading

1. Read `AGENTS.md`.
2. Read `docs/comic-spec.md`.
3. Read `config/languages.yaml` for the production language set.
4. Read `config/characters.yaml` when choosing reusable characters.

## Procedure

### 1. Choose/confirm target

If the user gives an SCP ID, use it. If the user asks you to choose, avoid IDs already present in:

- `state/used.json`
- `comics/queue/`
- `comics/done/`

Do not delete or rewrite `state/used.json` during script creation.

### 2. Read the live article

Fetch/read the live SCP article before writing. Do not rely on model memory or old summaries.

Default source policy:

- Build the comic from **Description**.
- Do not normally use Special Containment Procedures as panel text or scene material.
- If Special Containment Procedures is exceptionally useful, it may appear only in the final panel and only when it naturally completes panels 1-3.
- Do not mix Addenda, interviews, experiment logs, or incident logs into the normal main strip.
- Do not imitate official article images; use textual descriptions only.

If the live article cannot be read, stop and report that the script cannot be authored safely.

### 3. Draft the YAML

Create or update:

```text
comics/queue/scp-XXX.yaml
```

Required script qualities:

- `id` matches the filename.
- `title` is present where practical.
- `attribution.source_url` is present.
- `panels` form a coherent setup -> development -> reveal/turn -> payoff flow.
- Each `scene` is an English visual instruction for one depictable moment.
- Each visible person is listed in `characters`.
- Article-specific people go in `local_characters`; reusable/canon roles come from `config/characters.yaml`.
- Captions exist for all production languages and express the same source fact.
- `source` provenance is recommended for new/revised panels: `section`, `quote`, `url`, and optionally `fetched_at`.
- No dialogue bubbles are added for the current house style.

### 4. Internal review pass

Before calling the script done, switch to a reviewer mindset and produce findings first. Check:

- Description-first policy.
- Special Containment Procedures only as an exceptional final-panel payoff.
- No Addendum/interview/experiment-log leakage.
- Caption/scene consistency.
- Unsupported facts or invented causal links.
- Character key/name/order mistakes.
- Repeated composition/shot type.
- Weak or disconnected four-panel progression.
- Missing 15-language updates after semantic changes.

Apply only findings that are supported by the source article or project rules. Do not invent changes just to make a review non-empty.

### 5. Validate

Run validation for the edited script:

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml
```

For batch work, also run:

```bash
python scripts/validate_scripts.py --all
```

Fix all validation errors before finishing. Do not claim validation passed unless it actually ran.

### 6. Optional mock layout check

If the user asked for layout/overflow verification or the captions are long, run:

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

Mock output is disposable. Avoid full-comic mock runs over uncommitted accepted artwork.

## Completion report

Report:

- created/updated script path;
- source article used;
- whether Special Containment Procedures was used, and why;
- review findings applied or `no findings`;
- validation command result;
- next step: `$generate-scp-comic-images`.
