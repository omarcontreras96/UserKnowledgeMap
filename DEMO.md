# Demo script (about 4 minutes)

Every beat below has already worked in headless runs on 2026-09-20; the sample answers are in
`eval/samples/` if the live model misbehaves.

## Setup (2 minutes before)

```bash
cd bonsai
claude plugin list | grep -A3 bonsai        # must say "enabled" (the plugin is the hook install)
scripts/reset_demo.sh                                    # persona seed, empty log
python3 viz/serve.py &                                   # http://localhost:8766, click "fit"
```

If the plugin is not installed: `claude plugin marketplace add https://github.com/omarcontreras96/bonsai`
then `claude plugin install bonsai@bonsai --scope user`. Do NOT also run
`scripts/install_hooks.py`; that registers the same hooks a second time and everything fires twice.

Screen layout: browser with the map on the left half, a terminal with `claude` on the right half.
Start `claude` in any folder AFTER the reset so the SessionStart hook reads the clean seed.

## Beat 0: the problem (20 s)

"When you ask an AI to explain something, it guesses what you already know. It guesses wrong, uses
five terms you have never seen, and you either chase every one or give up. A teacher who knows the
class doesn't do that. This is a file that tells the agent what you know, that any agent can read,
and that learns from the conversation."

Point at the map: green is what the persona knows (business, economics), red is explicit gaps
(physics, calculus, logic, programming), grey is no data.

## Beat 1: the profile changes the explanation (60 s)

In `claude`:

> Why does a spinning top stay upright instead of falling over?

Expected: the answer says something like "two ideas explain it", builds from a rolling ball or a
bank balance, introduces angular momentum and precession only, never says torque or vector.

Say: "With no profile the same model opens with 'angular momentum, a vector', then torque, center
of mass, right angles. The eval on ten questions: unexplained concepts per answer went from 4.3
to 0.9." (Open `eval/results.md` if asked.)

Watch the map: within ~15 s the Stop hook adds the explained concepts under Physics > Mechanics >
Classical mechanics in blue. The change log fills on the right.

## Beat 2: the profile learns from the user (60 s)

> wait, what's torque again?

Expected: torque turns orange (asked) on the map at once, and the re-explanation uses door handles
and wrenches, nothing else. Say: "Asking about something you were just taught is evidence it did not
land. The file records that, and the next explanation starts lower."

> I already know what a vector is, you can use those.

Expected: Vector turns green, evidence "user-stated". Say: "Correcting the agent is a sentence, not
a database edit. That was one of the questions in the intro talk."

> Ok so the torque from gravity is what makes it precess sideways instead of falling.

Expected: torque and precession turn green (used), after a fast-model check that the sentence
actually applies the idea rather than name-dropping it.

## Beat 3: memory across sessions (40 s)

Exit `claude` (Ctrl+C twice or `/exit`). On the map, Classical mechanics turns from red to blue:
"the session-end pass consolidates. This is labeled as inferred or as aggregated evidence, and
rendered lighter, so a human can tell stored facts from beliefs."

Start `claude` again and ask:

> Now explain why a bicycle stays up when it's moving.

Expected: the answer uses torque and precession as known, and does not re-teach them. "Same file,
new session. Nothing lives in the harness."

Open `~/.bonsai/profile.json` in an editor for two seconds: "This is the whole memory. JSON,
one file, yours. Any agent that can read a file can use it."

## Beat 4: honest limits (20 s)

- "The one-line bio gets most of the single-answer gain. What the bio cannot do is learn, persist
  across agents, and get more precise. Those are the three things you just watched."
- "Used-correctly is model-judged and conservative. Prerequisite structure is model-supplied except
  in four domains where we validated it against a dataset."
- "A file listing what you don't know is more sensitive than one listing what you do. It stays in
  your home directory."

## If something breaks

- Map not updating: check the terminal running `viz/serve.py`; the page polls `/api/state` every 2 s.
- Torque not turning orange: the phrase must match "what is X" / "what's X" / "explain X" /
  "I don't understand X". Rephrase as "what is torque?".
- Stop hook slow: it is detached and depends on the OpenAI key in `~/.bonsai/.env`; 10-20 s is
  normal. Keep talking.
- Model ignores the profile: it happens on very short questions. Ask a "why does ..." question.
- Nuclear option: `scripts/reset_demo.sh` and restart `claude`.

## After the demo

```bash
claude plugin disable bonsai@bonsai   # hooks off, Claude behaves normally
claude plugin enable bonsai@bonsai    # back on before the next demo
```
