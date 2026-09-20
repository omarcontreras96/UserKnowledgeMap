# UserKnowledgeMap

A personal knowledge profile for AI agents. One JSON file, owned by the user, that any agent reads at
session start to explain things using only concepts the user already has, and updates from what
happens in conversation.

Built at the SundAI hack, 20 Sep 2026. See [PLAN.md](PLAN.md) for the design and build steps.

## Layout

```
data/      skeleton.json (Wikipedia outline, 3 levels), seed persona profiles
scripts/   build_skeleton.py, lib.py, render_context.py, hook scripts
hooks/     settings snippet for ~/.claude/settings.json
eval/      questions + eval runner
viz/       static tree view
```

## Setup

```bash
python3 -m venv ~/.venvs/ukm && ~/.venvs/ukm/bin/pip install -r requirements.txt
python3 scripts/build_skeleton.py          # writes data/skeleton.json
scripts/reset_demo.sh                       # copies the persona seed to $KNOWLEDGE_HOME
~/.venvs/ukm/bin/python scripts/install_hooks.py   # registers hooks in ~/.claude/settings.json
```

`KNOWLEDGE_HOME` defaults to `~/.knowledge`. The hooks that call a model read `OPENAI_API_KEY` from
`$KNOWLEDGE_HOME/.env` (one `KEY=value` line, chmod 600). The SessionStart hook needs no key.

## Status

- [x] Skeleton, persona seed, profile library
- [x] SessionStart hook: profile block changes how Claude explains (see `eval/samples/`)
- [x] UserPromptSubmit hook: "what's X" -> asked, "I already know X" -> used, correct use -> used; delta printed into context
- [ ] Stop hook (exposed), SessionEnd consolidation
- [ ] Tree visualization, eval, plugin packaging
