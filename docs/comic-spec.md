# SCP Comic Specification

This document contains stable project rules that should survive changes of agent/model. Agent-specific workflow belongs in `.agents/skills/`; runtime implementation belongs in `scripts/` and `config/`.

## 1. Source fidelity

1. Read the live SCP article before writing/revising a script.
2. **Description is the default and primary source for the four-panel comic.** Build panels 1–4 from the Description section whenever it contains enough material for a coherent strip.
3. **Do not normally use Special Containment Procedures in captions or scenes.** If containment procedures materially improve the story and are needed, use them only as the **fourth-panel payoff/aftermath**, after panels 1–3 have established the anomaly from Description. The transition must make narrative sense; do not jump from an unrelated Description fact to a random procedure merely because it is a procedure.
4. Addenda, interviews, incident logs, experiment logs, and other supplementary material should not be mixed into the main strip when doing so changes timeline/context. Use a separate comic or the top-level `addendum` when appropriate.
5. Captions should stay as close as practical to the source wording and must not introduce unsupported facts.
6. Scenes visualize the facts assigned to that panel; a scene must not add a causal relationship that the source does not support.
7. Existing article images are not visual source material. This is important because not every attachment shares the article's CC license.

## 2. Story structure

Default is four panels unless requested otherwise. The strip should have progression rather than four independent illustrations: setup, development, turn/reveal, and payoff/aftermath. Prefer a Description-only setup → development → reveal → payoff. When Special Containment Procedures are exceptionally used, they belong in panel 4 and should function as the consequence/response to what panels 1–3 revealed.

Avoid repeating the same shot. A useful default progression is wide/context → medium/action → close/reveal → medium or wide/payoff, but use the sequence that best fits the article.

## 3. Characters

Every visible person belongs in `panels[].characters`.

Reusable/canon project characters come from `config/characters.yaml`. Article-specific people are declared in top-level `local_characters`. Do not create a new named Foundation employee merely to fill a scene; use an existing generic attending researcher/D-Class/MTF role where appropriate.

Prefer the structured character form:

```yaml
local_characters:
  subject:
    name: "SCP-XXX"
    appearance: "stable physical traits"
    default_look: "default clothing/expression when the scene does not override it"
```

A panel may override clothing/equipment in `scene`. Make temporary protective equipment explicit enough that the image model does not blend it with the default outfit.

Use the same character name/key in the scene rather than switching to aliases such as "the subject". In multi-character scenes, list `characters` in the same order in which their actions are introduced in `scene`. When roles are visually ambiguous, explicitly place people left/right or otherwise spatially distinguish them.

For important colors, include numeric RGB alongside the color name when useful for cross-panel consistency.

## 4. Panel fields

`scene` is an English visual instruction. It specifies one depictable moment, not a sequence of several actions. It should include shot/composition, relevant expressions/actions/props, and temporary clothing/equipment when necessary. Do not put global art style into `scene`; style comes from `config/style.yaml`.

`caption` is required for the normal house style. Supported languages are defined by `config/languages.yaml`; currently the production set is ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant. **The 15 language values are translations of one semantic caption, not independently authored facts. If a human review changes caption meaning, every production language must be updated together.**

`source` is recommended provenance for new/revised panels. It may record `section` (`Description` by default, `Special Containment Procedures` only for the exceptional fourth-panel case), `quote`, `url`, and `fetched_at`. The source evidence is non-rendered and exists so future Codex reviews can distinguish source facts from presentation choices.

Only when the user explicitly approves an addendum or a non-final-panel use of Special Containment Procedures for a particular panel, that panel may use its actual `source.section` (for example, `Addendum 107-2` or `Special Containment Procedures`) with `source.exception: {user_approved: true, reason: "..."}`. Record the specific approved use in the non-empty reason; never infer approval or relabel evidence as Description. This is a per-panel exception, not permission for other panels or comics. It does not bypass required provenance or language checks. Without this explicit approval, Special Containment Procedures remain final-panel-only.

`notes` is optional non-rendered provenance/refinement guidance. Useful notes distinguish source fact, facts that must not change, and presentation choices that may change.

The current house style does not use character dialogue bubbles. Explanatory text is composited after image generation.

## 5. Image-generation constraints

The generated panel should contain artwork only. Captions/title/footer are added by Python. Prompt wording should avoid encouraging page layouts, grids, embedded text, empty speech bubbles, or multiple moments in one image.

**Every accepted source panel is normalized to the configured panel pixel size before composition and thumbnail generation.** The current layout uses a square panel. Image-generation/handoff workflows must explicitly request that same square pixel size and must not rely on an unconstrained aspect ratio.

Character identity consistency is more important than ornamental detail. When a provider supports references, character references and recent panel references may be supplied by the pipeline.

Generated candidates require visual review while the image model remains probabilistic. Variants are drafts; selected `output/<id>/panels/panel_N.png` files are the accepted source panels and must not be overwritten accidentally.

## 6. Thumbnail rule

`thumbnail.png` is derived **directly from the accepted first source panel** (`panels/panel_1.png`) after square normalization. It must never be cropped from a composed page such as `base.png` or a handoff/debug `generated-page.png`; doing so can capture gutters, borders, captions, or page framing.

## 7. Publication requirements

A comic is publishable only when all required production languages are successfully rendered and known blocking problems such as missing fonts/text overflow are absent. Unknown state is not equivalent to complete.

Every published comic preserves article attribution and CC BY-SA information. The project also discloses AI-generated artwork/translations in the rendered footer.

## 8. Validation principle

Rules that can be checked mechanically should be enforced by Python/schema/tests rather than existing only in agent instructions. Examples include required fields, valid language keys, character references, preset names, output completeness, square panel dimensions, and consistency between the script ID and expected file identity.
