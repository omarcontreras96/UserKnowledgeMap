#!/usr/bin/env python3
"""Portability: write the profile block into the instruction file another harness reads.

Any agent that reads a Markdown instructions file can use the same profile without hooks:

    export_context.py agents   # ./AGENTS.md        (OpenAI Codex CLI, many others)
    export_context.py gemini   # ./GEMINI.md        (Gemini CLI)
    export_context.py cursor   # ./.cursor/rules/knowledge-profile.mdc
    export_context.py claude   # ./CLAUDE.md        (Claude Code without the plugin)
    export_context.py all
    export_context.py agents --dir /path/to/project

The block is wrapped in markers so re-running replaces it in place and keeps the rest of the file.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from render_context import render  # noqa: E402

BEGIN, END = "<!-- knowledge-profile:begin -->", "<!-- knowledge-profile:end -->"
TARGETS = {
    "agents": "AGENTS.md",
    "gemini": "GEMINI.md",
    "claude": "CLAUDE.md",
    "cursor": ".cursor/rules/knowledge-profile.mdc",
}
CURSOR_FRONTMATTER = "---\ndescription: The user's knowledge profile; explain from what they know\nalwaysApply: true\n---\n"


def upsert(path: Path, block: str) -> str:
    wrapped = f"{BEGIN}\n{block}\n{END}"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if BEGIN in text and END in text:
            new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: wrapped, text, flags=re.S)
            action = "updated"
        else:
            new = text.rstrip("\n") + "\n\n" + wrapped + "\n"
            action = "appended to"
    else:
        head = CURSOR_FRONTMATTER if path.suffix == ".mdc" else ""
        new, action = head + wrapped + "\n", "created"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return action


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=[*TARGETS, "all"])
    ap.add_argument("--dir", type=Path, default=Path.cwd())
    args = ap.parse_args()
    profile = lib.load_profile()
    if not profile.get("nodes"):
        sys.exit("no profile at " + str(lib.profile_path()))
    block = render(profile)
    for t in (TARGETS if args.target == "all" else [args.target]):
        path = args.dir / TARGETS[t]
        print(f"{upsert(path, block)} {path}")


if __name__ == "__main__":
    main()
