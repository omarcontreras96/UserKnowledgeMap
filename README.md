# Bonsai

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
python3 -m venv ~/.venvs/bonsai && ~/.venvs/bonsai/bin/pip install -r requirements.txt
python3 scripts/build_skeleton.py          # writes data/skeleton.json
scripts/reset_demo.sh                       # copies the persona seed to $BONSAI_HOME
~/.venvs/bonsai/bin/python scripts/install_hooks.py   # registers hooks in ~/.claude/settings.json
```

`BONSAI_HOME` defaults to `~/.bonsai`.

### Install as a Claude Code plugin instead of editing settings.json

```bash
claude plugin marketplace add https://github.com/omarcontreras96/bonsai
claude plugin install bonsai@bonsai --scope user
```

Use one or the other: `install_hooks.py` (settings.json) or the plugin, not both, or every hook fires twice.
`BONSAI_DISABLED=1` silences the hooks for a session.

### Use the same profile from another agent

```bash
~/.venvs/bonsai/bin/python scripts/export_context.py agents   # AGENTS.md for Codex CLI / OpenClaw
~/.venvs/bonsai/bin/python scripts/export_context.py gemini   # GEMINI.md for Gemini CLI
~/.venvs/bonsai/bin/python scripts/chat_openai.py             # a chat REPL on OpenAI with the same hooks
``` The hooks that call a model read `OPENAI_API_KEY` from
`$BONSAI_HOME/.env` (one `KEY=value` line, chmod 600). The SessionStart hook needs no key.

## Status

- [x] Skeleton, persona seed, profile library
- [x] SessionStart hook: profile block changes how Claude explains (see `eval/samples/`)
- [x] UserPromptSubmit hook: "what's X" -> asked, "I already know X" -> used, correct use -> used; delta printed into context
- [x] Stop hook: concepts the agent explained -> exposed (detached worker, one fast-model call)
- [x] SessionEnd consolidation: parent exposed after >= 3 explained leaves, parent inferred from a used leaf, AL-CPL prerequisites inferred
- [x] Eval: 10 questions x {none, bio, tree}; Claude answers, gpt-5 judges. Unexplained dependencies per answer 4.3 -> 1.4 -> 0.9; follow-up questions 4.1 -> 2.7 -> 2.1. See `eval/results.md`.
- [x] Live tree visualization (`python3 viz/serve.py`, http://localhost:8766)
- [x] Demo script: `DEMO.md`
- [x] Plugin packaging: `.claude-plugin/`, `hooks/hooks.json` (install below)
- [x] Portability: `scripts/export_context.py` writes the block into AGENTS.md (Codex, OpenClaw), GEMINI.md, CLAUDE.md or Cursor rules; `scripts/chat_openai.py` is a second harness on OpenAI that reads and updates the same file
