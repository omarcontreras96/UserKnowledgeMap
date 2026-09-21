# Hooks

Two ways to register them, never both at once (they would fire twice):

- **Plugin (recommended):** `hooks/hooks.json` is loaded automatically when the plugin is installed
  (`claude plugin marketplace add https://github.com/omarcontreras96/UserKnowledgeMap`, then
  `claude plugin install user-knowledge-map@user-knowledge-map --scope user`). Turn off with
  `claude plugin disable user-knowledge-map@user-knowledge-map`.
- **settings.json:** `scripts/install_hooks.py` writes the same four hooks into `~/.claude/settings.json`
  (user scope); `--remove` takes them out. Useful for developing the hooks without reinstalling.

`UKM_DISABLED=1` silences the hooks for one session either way.

| Event | Script | What it does | stdout enters context? |
|---|---|---|---|
| SessionStart | `render_context.py` | prints the knowledge profile block | yes |
| UserPromptSubmit | `on_prompt.py` | detects "what is X" / "I already know X" / correct use; prints the delta | yes |
| Stop | `on_stop.py` | reads `last_assistant_message`, records explained concepts as `exposed` (detached) | no |
| SessionEnd | `on_session_end.py` | parent inference, cleanup | no |

Equivalent manual snippet for SessionStart only:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
        "command": "\"$HOME/.venvs/ukm/bin/python\" \"/ABS/PATH/UserKnowledgeMap/scripts/render_context.py\"",
        "timeout": 10 } ] }
    ]
  }
}
```

The profile lives in `$KNOWLEDGE_HOME` (default `~/.knowledge`). The hooks inherit Claude Code's
environment, so set `KNOWLEDGE_HOME` there if you want a different location.
