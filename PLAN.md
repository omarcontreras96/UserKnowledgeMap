# Personal Knowledge Map for AI Agents — build plan

SundAI hack, 20 Sep 2026. Steps are ordered by demo value; cut from the bottom.

## Decisions already made

- **Skeleton:** Wikipedia "Outline of academic disciplines", pruned to three levels:
  discipline (40) → field (~1,100) → subfield (~1,200). Bullets deeper than that are dropped.
  The five branches (Humanities, Social science, Natural science, Formal science, Applied science)
  are kept as a grouping label on each discipline, not as tree nodes.
- **Leaves:** concept-level nodes are *not* in the skeleton. They are proposed by the model on first
  contact and cached in the profile under the subfield they belong to (`source: "generated"`).
- **Prerequisites:** the skeleton is containment (torque is *inside* classical mechanics), not
  prerequisites (torque *requires* force and vectors). Prerequisite reasoning is delegated to the
  model at explanation time via the dependency check in the rules block (step 3). Real prerequisite
  edges exist only where AL-CPL gives them (geometry, physics, precalculus, data mining) and are used
  for consolidation inference as a stretch. Say this out loud on the slide.
- **Storage:** `~/.knowledge/profile.json` (current state) + `~/.knowledge/log.jsonl` (append-only diffs).
  `KNOWLEDGE_HOME` env var overrides the directory so the demo can point at the repo.
- **Harness:** Claude Code hooks in `~/.claude/settings.json` first; plugin packaging last.
- **Models:** `claude-haiku-4-5-20251001` inside hooks (latency), `claude-sonnet-5` for eval
  generation, `claude-opus-5` as eval judge. Load the `claude-api` skill before writing API code.
- **Persona for the demo:** MBA, business undergrad, ex-consulting. Strong in business/economics,
  exposed to literature/history, explicit gaps in physics, calculus, logic.

## Data model

```jsonc
// profile.json
{
  "version": 1,
  "owner": "persona:mba",
  "nodes": {
    "economics/microeconomics": { "state": "used",    "evidence": "seed", "updated_at": "…" },
    "physics/classical-mechanics": { "state": "unknown", "evidence": "seed", "updated_at": "…" },
    "physics/classical-mechanics/torque": {            // generated leaf
      "state": "asked", "source": "generated", "name": "Torque",
      "evidence": "session 3f2a turn 4", "updated_at": "…"
    }
  }
}
```

States, in order of strength: `unknown` (explicitly established gap) < `exposed` (an agent explained
it) < `used` (user employed it correctly). Two side states: `asked` (user asked "what is X"; overrides
`exposed`, since asking about something you were taught is evidence it did not land) and `inferred`
(set by parent/prerequisite inference, never by direct evidence; renders lighter in the tree).
Absence from `nodes` means "no data", which is different from `unknown`.
Precedence when transitions conflict: user-stated evidence > direct evidence (`asked`, `used`,
`exposed`) > `inferred`. Within direct evidence, a stronger state only gets replaced by `asked`.

Node id = skeleton path of slugs. Only one field describes certainty (`state`); no separate confidence.

## Steps

### 0. Scaffold (15 min)
```
knowledge-map/
  data/            skeleton.json, seed profile, AL-CPL edges
  scripts/         build_skeleton.py, render_context.py, on_prompt.py, on_stop.py, on_session_end.py, lib.py
  hooks/           settings.snippet.json (what goes into ~/.claude/settings.json)
  eval/            questions.json, run_eval.py, results.md
  viz/             index.html
  PLAN.md  README.md
```
`git init`, Python 3 stdlib + `anthropic` only. No node_modules (folder is iCloud-synced).
**Done when:** repo exists, `python3 -c "import anthropic"` works, `ANTHROPIC_API_KEY` set.

### 1. Build the skeleton (30 min)
`scripts/build_skeleton.py`: fetch the outline wikitext via the MediaWiki API
(`action=parse&page=Outline_of_academic_disciplines&prop=wikitext`), stop at `== See also`,
parse H2 → branch, H3 → discipline, `*` → field, `**` → subfield, ignore deeper bullets.
Clean-up rules:
- strip `(outline)` links, `{{…}}` templates, italic notes;
- dedupe by Wikipedia title (Modal logic appears under two parents: keep first, record `also_under`);
- drop known junk subtrees by name list (e.g. the Aerospace tourism list under Physical science);
- slug ids: `formal-science/logic/mathematical-logic/modal-logic` style, lowercase, ascii.
Write `data/skeleton.json` with `nodes[id] = {name, level, parent, branch, wiki_title}` and a
`children` index. Print counts per level.
**Done when:** counts are roughly 40 / 1,100 / 1,200 and `logic` and `literature` branches look sane.

### 2. Seed profile for the persona (20 min)
`data/profile.persona-mba.json`, hand-written, ~30 entries at discipline/field level only:
- `used`: business, economics (micro/macro), accounting, marketing, statistics basics
  (descriptive statistics), management.
- `exposed`: English literature, history (modern), philosophy (ethics), psychology (cognition).
- `unknown` (explicit): physics (classical mechanics, electromagnetism), mathematics beyond
  algebra (calculus, linear algebra, probability theory), logic (mathematical logic), computer science
  (algorithms, programming).
Copy to `$KNOWLEDGE_HOME/profile.json` with a `make reset` / `scripts/reset_demo.sh`.
**Done when:** the file validates against the skeleton (every id exists) via `lib.validate()`.

### 3. Context renderer + SessionStart hook (45 min) — first demoable moment
`scripts/render_context.py` reads profile + skeleton, prints a block ≤ ~450 tokens. The rules
section is the product: it turns the profile into teaching behavior.
```
<knowledge-profile>
This user's knowledge map (owner-maintained; treat as ground truth about what they know).
KNOWS WELL: Economics, Business, Statistics (descriptive)
HAS SEEN BUT MAY NOT RECALL: English literature, Modern history, Ethics
DOES NOT KNOW: Classical mechanics, Calculus, Linear algebra, Probability theory, Mathematical logic, Algorithms
Recently asked about (explain from scratch if it comes up again): Torque

How to explain things to this user:
1. Before answering, silently list the concepts your explanation rests on.
2. For each one that is not in KNOWS WELL: either replace it with something the user already
   knows (analogies from KNOWS WELL areas are welcome), or introduce it explicitly, defined only
   from concepts the user knows.
3. Introduce at most two new concepts per answer. Never use a third unknown concept to define
   the second. If the question genuinely needs more, teach the first two and say what comes next.
4. Do not simplify areas in KNOWS WELL; assume full fluency there.
5. Areas not listed: use your judgment, leaning toward step 2.
6. If the user says they already know, or do not know, something, believe them; the profile
   will be updated.
Keep this profile out of your replies unless asked.
</knowledge-profile>
```
Roll-up rule: if a discipline's touched children all share a state, print the discipline, not the children.
Register in `~/.claude/settings.json`:
```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "python3 /ABS/PATH/knowledge-map/scripts/render_context.py" } ] } ] } }
```
**Done when:** a fresh `claude` session asked "why does a spinning top stay up?" defines torque and
angular momentum inline instead of assuming them. Compare against a session with the hook disabled.

### 4. UserPromptSubmit hook: detect asked/used, inject the delta (45 min)
`scripts/on_prompt.py` reads stdin JSON, takes `user_input`:
- **asked:** regex (`what(?:'s| is| does) (.+?)( mean)?\?`, "explain X", "I don't know what X is")
  → resolve X against skeleton names + generated leaves (case-insensitive, fuzzy on word overlap);
  set `asked`.
- **used:** if the message contains a node name and is not a question about it → set `used`.
  Cheap and noisy on purpose; call Haiku to confirm "used correctly" only if time allows.
- **correction by talking** (answers the talk's "can users correct an agent without becoming its
  DBA?"): `I (already) know X`, `I'm familiar with X`, `you can assume X` → `used`, evidence
  `user-stated`; `I don't know X`, `I've never heard of X`, `never learned X` → `unknown`, evidence
  `user-stated`. User statements outrank every other transition, including `inferred`.
- Unresolvable X → create a generated leaf under the most recently `exposed` subfield in this session
  (session id → last touched subfield, stored in `$KNOWLEDGE_HOME/session-<id>.json`).
Print to stdout (enters Claude's context): `Knowledge profile update: "Torque" → asked (was: exposed).
Explain it from scratch.` Append diff to `log.jsonl`.
**Done when:** typing "wait, what's torque?" mid-session produces a visibly simpler re-explanation and
a new line in `log.jsonl`; typing "I already know what a vector is" turns `vector` green without
touching any file.

### 5. Stop hook: detect exposed (45 min)
`scripts/on_stop.py` reads stdin JSON, uses `last_assistant_message` (do not read the transcript;
it lags). Skip if the message is < 300 chars or contains no prose (pure code/tool output).
Else call Haiku with: the message, the list of touched skeleton nodes + their subfields for the active
disciplines, and ask for JSON `{ "exposed": [ {"name", "parent_subfield_id"} ] }` constrained to
existing subfield ids as parents. Apply: existing node → `exposed` only if current state is weaker;
new name → generated leaf, `exposed`. Append diff. Run detached (`subprocess.Popen` + exit 0
immediately) so the turn never blocks on the API call.
**Done when:** after Claude explains the spinning top, `profile.json` gains `torque` and
`angular-momentum` leaves under `physics/classical-mechanics` in state `exposed`.

### 6. SessionEnd consolidation (20 min)
`scripts/on_session_end.py`: parent inference (a `used` leaf marks its subfield ≥ `inferred`; a
subfield with ≥ 3 `exposed` leaves marks itself `exposed`), drop session scratch file, one log line.
Stretch: AL-CPL prerequisite edges for the four covered domains → mark prerequisites `inferred`.
**Done when:** ending the demo session updates `physics/classical-mechanics` to `exposed`.

### 7. Tree visualization (60 min)
`viz/index.html`, static, D3 from cdnjs. Loads `skeleton.json` + `profile.json` (served by
`python3 -m http.server` from the repo, with `$KNOWLEDGE_HOME` symlinked in). Collapsible tree or
sunburst, only disciplines expanded by default, colored by state:
used = green, exposed = blue, asked = orange, inferred = light blue, unknown = red, no data = grey.
Right panel tails `log.jsonl`. Poll both files every 2 s so the recolor happens live during the demo.
**Done when:** the "asked → used" transition is visible without reloading.

### 8. Eval (60 min) — run this as soon as step 3 works, in parallel with 4–7
`eval/questions.json`: 10 questions the persona would ask, spread across the map (2 physics,
2 math, 1 logic, 1 CS, 2 literature/history, 2 economics as controls where the persona is strong).
`eval/run_eval.py`: three conditions per question, generation with Sonnet 5:
- A: no profile; B: one-line bio ("MBA, business undergrad, ex-consulting"); C: rendered tree block.
Judge with Opus 5, given the persona profile:
- **unexplained-dependency count:** concepts used without inline definition that the persona has
  `unknown` / no entry for;
- **follow-up count:** judge writes the persona's next message; count "what is X" questions;
- **new-concept count:** concepts introduced with a definition; the budget rule says ≤ 2, so this
  checks that condition C actually follows the rules rather than just adding caveats.
Also record answer length (the tree should not just make answers longer).
Output `eval/results.md` as a table, means per condition. Put it on the final slide.
**Done when:** the table exists. If C does not beat B, revise the rules text in step 3 and rerun.

### 9. Demo script (20 min)
1. `scripts/reset_demo.sh`, open viz, open `claude`.
2. "Why does a spinning top stay upright instead of falling?" → explanation defines torque and
   angular momentum inline (SessionStart block).
3. "Wait, what's torque again?" → `asked`, orange in tree, log line, re-explanation built only from
   things the persona knows (no force vectors; a wrench and a door handle instead).
4. "I already know what a vector is, you can use those." → `vector` turns green with evidence
   `user-stated`; next explanation uses vectors. Correction by talking, no file edits.
5. "Ok so the torque from gravity is what makes it precess instead of tip." → `used`, green.
6. Exit session → `physics/classical-mechanics` turns from red to blue (consolidation), shown as
   `inferred`, lighter, because no direct evidence set it.
7. Show `profile.json` in an editor: human-readable, editable, portable. Show eval table.

### 10. Plugin packaging (30 min, only if everything above is green)
`.claude-plugin/plugin.json`, `hooks/hooks.json` with the four hooks, `.claude-plugin/marketplace.json`,
install at user scope. Move the settings.json snippet out.

### 11. Stretch: portability
Same `profile.json` read by a second harness (OpenClaw `before_prompt_build` / `agent_end`), proving
the file, not the harness, is the memory.

## How this answers the hackathon theme (put on the pitch slide)
- **Memory in tokens:** one JSON file, human-readable, editable in any editor, readable by any
  harness. Editability, portability, shareability as designed.
- **"Can users correct an agent without becoming its DBA?"** Yes: "I already know X" in
  conversation updates the file. Editing JSON is available, never required.
- **"Stored facts, inferred beliefs, or both?"** Both, labeled. `inferred` is a distinct state with
  no direct evidence and renders lighter; every other node carries an evidence pointer to the turn
  that set it.
- **"How do you merge memories of different agents?"** By state strength with evidence kept; the
  append-only log is the merge history. Two harnesses writing the same file is the portability demo.
- **Staleness:** detected behaviorally. `asked` after `exposed` means the earlier explanation did not
  stick. **Conflicts:** resolved by the strength ordering, user statements on top. **Sparse signals:**
  `used` is rare and we say so, rather than pretending every turn is evidence.
- **Where memory lives:** personal infrastructure (the user's home directory), read by the harness
  through hooks. The harness is a reader, not the owner.

## Known limitations to say out loud
- "used correctly" is pattern/model-judged; the tree can drift confidently.
- Wikipedia outline is uneven (some disciplines have 5 fields, some 80) and is a taxonomy of fields,
  not a curriculum. Prerequisite structure is supplied by the model at explanation time and only
  dataset-validated in the four AL-CPL domains.
- The tree-beats-bio hypothesis is untested until the eval runs. If the tree only matches a one-line
  bio on a single answer, the product story is what the bio cannot do: learn from interaction,
  persist across sessions and agents, and get more precise over time.
- Claude Code is a coding tool; learning conversations mostly happen elsewhere. It is the only
  harness with hooks we can use today. The file is the product; Claude Code is one reader.
- A file listing what you do not know is more sensitive than one listing what you do; it lives in the
  user's home directory and never leaves the machine in this build.
- Knowledge decay, multi-user, real intake (Takeout/CV/transcript), and a freeform bucket for
  off-taxonomy knowledge are out of scope today.
