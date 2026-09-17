# SCP Comic Specification

This document contains stable project rules that should survive changes of agent/model. Agent-specific workflow belongs in `.agents/skills/`; runtime implementation belongs in `scripts/` and `config/`.

## 1. Source fidelity

1. Read the live SCP article before writing/revising a script.
2. The main comic is grounded in Special Containment Procedures and Description.
3. Addenda, interviews, incident logs, and experiment logs should not be mixed into the main strip when doing so changes timeline/context. Use a separate comic or the top-level `addendum` when appropriate.
4. Captions should stay as close as practical to the source wording and must not introduce unsupported facts.
5. Scenes visualize the facts assigned to that panel; a scene must not add a causal relationship that the source does not support.
6. Existing article images are not visual source material. This is important because not every attachment shares the article's CC license.

## 2. Story structure

Default is four panels unless requested otherwise. The strip should have progression rather than four independent illustrations: setup, development, turn/reveal, and payoff/aftermath. Do not force comedy when it would require inventing facts; the documentary/SCP-record contrast can itself provide the payoff.

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

`caption` is required for the normal house style. Supported languages are defined by `config/languages.yaml`; currently the production set is ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant.

`notes` is optional non-rendered provenance/refinement guidance. Useful notes distinguish source fact, facts that must not change, and presentation choices that may change.

The current house style does not use character dialogue bubbles. Explanatory text is composited after image generation.

## 5. Image-generation constraints

The generated panel should contain artwork only. Captions/title/footer are added by Python. Prompt wording should avoid encouraging page layouts, grids, embedded text, empty speech bubbles, or multiple moments in one image.

Character identity consistency is more important than ornamental detail. When a provider supports references, character references and recent panel references may be supplied by the pipeline.

Generated candidates require visual review while the image model remains probabilistic. Variants are drafts; selected `output/<id>/panels/panel_N.png` files are the accepted source panels and must not be overwritten accidentally.

## 6. Publication requirements

A comic is publishable only when all required production languages are successfully rendered and known blocking problems such as missing fonts/text overflow are absent. Unknown state is not equivalent to complete.

Every published comic preserves article attribution and CC BY-SA information. The project also discloses AI-generated artwork/translations in the rendered footer.

## 7. Validation principle

Rules that can be checked mechanically should be enforced by Python/schema/tests rather than existing only in agent instructions. Examples include required fields, valid language keys, character references, preset names, output completeness, and consistency between the script ID and expected file identity.
