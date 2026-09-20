# Data

| File | What | Source | License |
|---|---|---|---|
| `outline.wikitext` | raw source of the skeleton (cached so builds are offline and deterministic) | Wikipedia, [Outline of academic disciplines](https://en.wikipedia.org/wiki/Outline_of_academic_disciplines) | CC BY-SA 4.0 |
| `skeleton.json` | discipline → field → subfield tree, ~55 / 1,000 / 1,000 nodes; built by `scripts/build_skeleton.py` | derived from the above | CC BY-SA 4.0 |
| `prereqs.json` | direct concept-prerequisite edges for four domains (physics, geometry, precalculus, data mining); built by `scripts/fetch_alcpl.py` | [AL-CPL](https://github.com/harrylclc/AL-CPL-dataset), Liang et al. 2018, on the Wiki concept map of Wang et al. 2016 | CC BY-NC-SA 4.0 (non-commercial; hackathon use) |
| `profile.persona-*.json` | hand-written seed profiles for demo personas | this repo | same as repo |

The skeleton is containment (torque is *inside* classical mechanics), not a curriculum (torque
*requires* force). Prerequisite reasoning at explanation time is delegated to the model through the
rules block; `prereqs.json` is used only for consolidation inference in the four domains it covers.
