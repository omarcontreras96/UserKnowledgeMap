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
- **Storage:** `~/.bonsai/profile.json` (current state) + `~/.bonsai/log.jsonl` (append-only diffs).
  `BONSAI_HOME` env var overrides the directory so the demo can point at the repo.
- **Harness:** Claude Code hooks in `~/.claude/settings.json` first; plugin packaging last.
- **Models:** the user has an OpenAI key, so hooks and eval call OpenAI: `gpt-5-mini` inside hooks
  (latency), `gpt-5` for eval generation and judging. Override with `BONSAI_MODEL_FAST`, `BONSAI_MODEL_GEN`,
  `BONSAI_MODEL_JUDGE`. The key is read from `~/.bonsai/.env` (never committed). The agent being
  profiled is still Claude in Claude Code; only the bookkeeping calls use OpenAI.
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
Copy to `$BONSAI_HOME/profile.json` with a `make reset` / `scripts/reset_demo.sh`.
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
**Done 2026-09-20:** see `eval/samples/spinning-top-*.md`. Control opens with "angular momentum, a
vector" and uses torque, center of mass, right angles. Profile run says "two ideas make that work",
builds from a rolling ball, introduces only angular momentum and precession, never says torque or vector.

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
  (session id → last touched subfield, stored in `$BONSAI_HOME/session-<id>.json`).
Print to stdout (enters Claude's context): `Knowledge profile update: "Torque" → asked (was: exposed).
Explain it from scratch.` Append diff to `log.jsonl`.
**Done when:** typing "wait, what's torque?" mid-session produces a visibly simpler re-explanation and
a new line in `log.jsonl`; typing "I already know what a vector is" turns `vector` green without
touching any file.
**Done 2026-09-20:** regex detection for asked / user-stated known / user-stated unknown; `used`
detection over tracked names with a fast-model "used correctly" check; unresolvable terms placed by a
fast-model call (`is_concept` gate rejects comparisons like "the difference between micro and macro");
canonical-name dedupe with aliases. Live headless run logged `physics/mechanics/torque -> asked`.

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
**Done 2026-09-20:** live two-session test. Session 1 (spinning top) -> spin, angular momentum,
precession, torque, friction all `exposed` under `physics/mechanics/classical-mechanics`, hook returned
in 50 ms, worker finished in ~15 s. Session 2 (user restates it in their own words) -> precession and
friction `used`. Names are filtered to textbook-index form (1-3 words, no "X and Y" compounds); the
worker runs the fast model at low reasoning since latency is free when detached. Stem matching lets
"precess"/"precessing" hit "precession". Profile writes go through a file lock because the Stop
worker and the next UserPromptSubmit hook can overlap.

### 6. SessionEnd consolidation (20 min)
`scripts/on_session_end.py`: parent inference (a `used` leaf marks its subfield ≥ `inferred`; a
subfield with ≥ 3 `exposed` leaves marks itself `exposed`), drop session scratch file, one log line.
Stretch: AL-CPL prerequisite edges for the four covered domains → mark prerequisites `inferred`.
**Done when:** ending the demo session updates `physics/classical-mechanics` to `exposed`.
**Done 2026-09-20:** rules 1-2 only climb from conversation-generated leaves (seeded skeleton fields
never promote their discipline). AL-CPL wired: `data/prereqs.json` (382 concepts, 569 direct edges
after transitive reduction); a used leaf marks missing prerequisites `inferred` (torque -> lever).
Live: SessionEnd fires in headless mode; `physics/mechanics/classical-mechanics` went unknown ->
exposed with evidence naming the five concepts. In headless runs the session ends before the Stop
worker finishes, so consolidation lands at the next session end; interactive sessions are long
enough that this does not matter. Stale session files are swept after 6 h.

### 7. Tree visualization (60 min)
`viz/index.html`, static, D3 from cdnjs. Loads `skeleton.json` + `profile.json` (served by
`python3 -m http.server` from the repo, with `$BONSAI_HOME` symlinked in). Collapsible tree or
sunburst, only disciplines expanded by default, colored by state:
used = green, exposed = blue, asked = orange, inferred = light blue, unknown = red, no data = grey.
Right panel tails `log.jsonl`. Poll both files every 2 s so the recolor happens live during the demo.
**Done when:** the "asked → used" transition is visible without reloading.
**Done 2026-09-20:** `viz/serve.py` + `viz/index.html`. Every discipline drawn (grey when untouched,
compressed spacing), full path of every profile node, pan/zoom/fit, pulse on change, log panel.
Verified live: "what's torque?" turned orange within 2 s, "I already know vectors" turned green.

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
**Done 2026-09-20** (`eval/results.md`; generator = Claude via headless `claude -p` with the condition
appended to the system prompt, judge = gpt-5, n = 10):

| condition | unexplained deps | follow-up questions | new concepts | words |
|---|---|---|---|---|
| A none | 4.30 | 4.10 | 6.7 | 380 |
| B bio  | 1.40 | 2.70 | 7.0 | 430 |
| C tree | 0.90 | 2.10 | 6.7 | 421 |

On the six questions in areas the persona does not know: unexplained 5.50 -> 1.50 -> 0.83,
follow-ups 5.50 -> 3.00 -> 2.50. Controls in known areas stayed at 0 unexplained under all conditions
(the profile does not dumb down strong areas). Answers under C are ~10% longer than A, not 2x.
Honest reading: the one-line bio captures most of the single-answer gain (4.3 -> 1.4); the tree adds
a smaller, consistent improvement (C <= B on 8 of 10 questions). With n = 10 the B-vs-C gap is within
noise. The "at most two new concepts" budget is not obeyed (C defines ~6 per answer by the judge's
count, which includes analogies and sub-points). The product claim therefore rests on what the bio
cannot do: learn from the conversation, persist across sessions and agents, and get more precise.

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
**Done 2026-09-20:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json`
using `${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh` (picks the venv python if present). Validated with
`claude plugin validate`. settings.json install kept as the demo path; the two must not coexist.

### 11. Stretch: portability
Same `profile.json` read by a second harness (OpenClaw `before_prompt_build` / `agent_end`), proving
the file, not the harness, is the memory.
**Done 2026-09-20, two ways:** (a) `scripts/export_context.py` writes the block into AGENTS.md, which
OpenClaw and Codex CLI inject into every session (also GEMINI.md, CLAUDE.md, Cursor rules), idempotent
via markers; (b) `scripts/chat_openai.py`, a REPL on gpt-5 that runs the same on_prompt / on_stop /
consolidation code against the same file. Verified: spinning top on gpt-5-mini -> angular momentum,
torque, precession exposed; "what is precession again?" -> asked; session end -> classical mechanics
exposed. The map shows it live exactly as for Claude Code.

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
