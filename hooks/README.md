# Hooks

`scripts/install_hooks.py` writes these into `~/.claude/settings.json` (user scope, all projects).
`scripts/install_hooks.py --remove` takes them out again. A backup of settings.json is made each time.

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
