#!/usr/bin/env python3
"""Register this repo's hooks in ~/.claude/settings.json (user scope), idempotently.

Usage: install_hooks.py [--remove] [--settings PATH]
Backs up the settings file to settings.json.bak-<timestamp> before writing.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = Path.home() / ".venvs" / "bonsai" / "bin" / "python"
if not PY.exists():
    PY = Path(sys.executable)
MARK = "bonsai"

# event -> (script, timeout seconds). Only the scripts that exist are installed.
HOOKS = {
    "SessionStart": ("render_context.py", 10),
    "UserPromptSubmit": ("on_prompt.py", 15),
    "Stop": ("on_stop.py", 5),
    "SessionEnd": ("on_session_end.py", 30),
}


def command_for(script: str) -> str:
    return f'"{PY}" "{ROOT / "scripts" / script}"  # {MARK}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--settings", type=Path, default=Path.home() / ".claude" / "settings.json")
    args = ap.parse_args()

    settings = json.loads(args.settings.read_text()) if args.settings.exists() else {}
    hooks = settings.setdefault("hooks", {})

    # strip anything we installed before
    for event in list(hooks):
        hooks[event] = [g for g in hooks[event]
                        if not any(MARK in h.get("command", "") for h in g.get("hooks", []))]
        if not hooks[event]:
            del hooks[event]

    installed = []
    if not args.remove:
        for event, (script, timeout) in HOOKS.items():
            if not (ROOT / "scripts" / script).exists():
                continue
            hooks.setdefault(event, []).append({
                "hooks": [{"type": "command", "command": command_for(script), "timeout": timeout}]
            })
            installed.append(f"{event} -> scripts/{script}")
    if not hooks:
        settings.pop("hooks", None)

    if args.settings.exists():
        shutil.copy(args.settings, args.settings.with_suffix(f".json.bak-{int(time.time())}"))
    args.settings.parent.mkdir(parents=True, exist_ok=True)
    args.settings.write_text(json.dumps(settings, indent=2) + "\n")
    print("removed bonsai hooks" if args.remove else "installed:\n  " + "\n  ".join(installed))
    print(f"settings: {args.settings}")


if __name__ == "__main__":
    main()
