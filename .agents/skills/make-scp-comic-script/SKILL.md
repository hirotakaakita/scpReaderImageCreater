---
name: make-scp-comic-script
description: Create or revise one SCP comic script YAML from the live SCP article. For a combined script-and-images request, continue with generate-scp-comic-images after validation.
---

# Make SCP comic script

Use for: `scp-XXX の漫画台本を作って`, `台本を作って`, `N本分の台本を作って`.

For a script-only request, stop after validation. When the user also requests image generation, continue directly with `$generate-scp-comic-images` after internal review and successful validation. Do not insert a human script or prompt approval step unless requested; report the combined result after image generation.

## Read only

- `AGENTS.md`
- `docs/comic-spec.md`
- target live SCP article
- `config/languages.yaml`
- `config/characters.yaml` only if choosing reusable characters
- existing target YAML only when revising
- `scripts/lib/official_titles.py` and the target SCP's entries in the language catalogs under `../scpjpReaderActions/local-data/` (or `SCP_READER_DATA_DIR`) when resolving titles; do not dump whole catalogs

Do not read README or unrelated SCP YAML unless the user asks.

## Script style

The user-approved published SCP-105 rendering style is fixed for future scripts and generation until the user explicitly changes it. Follow `config/style.yaml` and the primary visual reference `config/style_references/approved_published_style.png` maintained by `$generate-scp-comic-images`; do not introduce an alternative rendering style in scene descriptions. This fixes drawing technique, not camera angles, poses, character identities or source-described colors.

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

## Preserve mechanisms when condensing

- Name the acting SCP or component explicitly when explaining an effect. Choose supporting details according to the SCP and the explanation; input-to-output pairings are not mandatory and need stating only when necessary for understanding or avoiding ambiguity.
- Preserve event intervals, duration limits, simultaneous actions, and before/during/after relationships. Do not merge an effect during an event with an effect after it.
- Keep conditional effects conditional, including what happens when an action is prevented. Preserve thresholds, inequalities, maxima, and the measured quantity (for example, radius rather than area). State duration relationships explicitly rather than implying a fixed duration.
- Fit the four panels around the main mechanism, not the default beat labels. If an important mechanism needs two panels, remove a less relevant detail instead of shortening away its conditions or sequence.

## Japanese narration

Write Japanese captions and explanatory addendum prose consistently in polite です・ます style. Avoid mixing plain-form sentence endings or noun-ending fragments (体言止め) into narration; for example, use `赤い錠剤です。` rather than `赤い錠剤。`. Preserve natural subordinate clauses, source facts, measurements, and uncertainty. Keep official titles, proper names, and direct quotations unchanged.

Include Japanese sentence-ending consistency in internal review. A style-only correction that preserves meaning may update Japanese alone; semantic changes still require all production languages.

## Official titles

Populate the YAML `title` mapping for every production language from the official SCP titles, not an invented comic headline, a paraphrase of the Description, or an independently translated title. This applies to new scripts and revisions.

Use `official_title_for(comic_id, lang)` from `scripts/lib/official_titles.py` for each language. It reads the matching `numericItemId` entry's `titleJP` field in the reader's language-specific `scp-data.json` catalog and returns the title with its SCP number. Preserve the returned wording. Honor `SCP_READER_DATA_DIR` when configured. Do not use `official_titles_for()` for this step: its fallback can silently reuse a handwritten YAML title.

If lookup fails or returns an untranslated placeholder, verify the title against that language's official SCP Wiki article or series index. If no official localized title exists, use the verified English official title and report that fallback. If no official title can be verified, report the unresolved language rather than inventing one or treating the title as complete. The helper's English fallback for translation placeholders is allowed, but report it as a fallback too.

## People in scenes

Choose whether to include people based on the explanatory composition; neither require nor exclude them by default. Do not add blanket `No people` instructions in the name of source fidelity. Reserve an explicit people-free constraint for a user request or a scene-specific need. Supporting figures observing or examining the subject are allowed, but must not introduce unsupported anomalous effects or causal claims.

## Visual staging

Stage scenes for source-faithful explanatory illustrations. Keep rendering direction centralized in `$generate-scp-comic-images` and `config/style.yaml`: the default follows the user-designated published SCP-105 images, combining delicate manga-influenced faces, soft dimensional painted shading, realistic materials and dark subdued cinematic backgrounds. Neither the old LoRA configuration nor the later F variant defines this reference. Preserve source-described ages, identities, colors and physical properties. Keep the SCP or relevant detail readable at smartphone size without inventing luminous effects or comedic actions. Put shot distance, camera angle and purposeful action in the scene, not conflicting global style requirements.

## Composition and pose variety

Plan the four scenes together, choosing framing for each explanatory beat rather than repeating an eye-level three-quarter view. In each `scene`, specify shot distance, camera angle, subject placement, and, when people appear, their relevant action, posture, hand placement, and gaze. Vary these deliberately between adjacent panels where useful: an establishing view, a material close-up, an overhead interaction, or an over-the-shoulder view are options, not a fixed four-shot template.

Avoid repeatedly staging a scientist leaning over a table, holding a clipboard, or pointing at the SCP when those actions add no information. Use natural, scene-appropriate poses; a hands-only detail or an unobstructed SCP view may communicate better than another observer portrait. Do not add people or invent actions merely for variety. Preserve source-required immobility, physical constraints, and spatial continuity; a repeated angle or pose is appropriate for a deliberate before/after comparison or when required by the explanation. Change the camera instead of moving an immobile subject.

## Steps

1. Confirm the SCP ID. If choosing automatically, avoid `state/used.json`, `comics/queue/`, and `comics/done/`.
2. Create the mechanical YAML skeleton first when starting a new script:

```bash
python scripts/create_script_stub.py scp-XXX --quiet
```

3. Read the live SCP article. Write from the article, not memory.
4. Fill the YAML in `comics/queue/scp-XXX.yaml`.
   - Resolve every `title` entry using the Official titles rules above.
   - Use source-backed explanatory captions, not vague summaries.
   - Description is the default source.
   - Special Containment Procedures may be used only as the final-panel explanatory payoff.
   - Include per-panel `source` provenance for new scripts.
   - Fill all production-language captions with the same meaning.
5. Do a short internal review:
   - all title entries match verified official titles, with any English fallbacks identified;
   - caption facts checked against the relevant live Description passage, not just the short source.quote;
   - clear subjects and source-faithful conditions, timing, and numerical limits in every language, with supporting details appropriate to the SCP;
   - caption/scene consistency;
   - varied, explicitly staged framing and human poses across the four scenes, with purposeful rather than accidental repetition;
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
- title source and any fallback or unresolved languages
- whether Special Containment Procedures were used, and why
- validation result
- next step: `$generate-scp-comic-images`
