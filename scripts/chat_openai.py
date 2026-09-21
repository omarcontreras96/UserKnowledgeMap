#!/usr/bin/env python3
"""A second harness: a 60-line chat REPL on OpenAI that reads and updates the SAME profile file.

This is the portability demo. Nothing here is Claude-specific: the profile block goes into the
system prompt, the user's message goes through on_prompt (asked / used / corrections), the reply
goes through on_stop (exposed), and the map at http://localhost:8766 updates exactly as it does for
Claude Code, because the file is the memory, not the harness.

    ~/.venvs/bonsai/bin/python scripts/chat_openai.py            # uses BONSAI_MODEL_GEN (gpt-5)
    ~/.venvs/bonsai/bin/python scripts/chat_openai.py --model gpt-5-mini
Type /quit to leave (runs the session-end consolidation).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import uuid
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import on_prompt  # noqa: E402
import on_session_end  # noqa: E402
import on_stop  # noqa: E402
from render_context import render  # noqa: E402


def run_prompt_hook(session_id: str, text: str) -> str:
    """Same code path as the Claude Code hook; returns the delta text it would inject."""
    buf = io.StringIO()
    with redirect_stdout(buf), lib.locked():
        on_prompt._run(text, session_id)
    return buf.getvalue().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=lib.MODEL_GEN)
    args = ap.parse_args()
    client = lib.openai_client(timeout=120)
    session_id = f"openai-{uuid.uuid4().hex[:8]}"
    history: list[dict] = []
    print(f"[{args.model}] reading {lib.profile_path()}  (type /quit to end)\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            text = "/quit"
        if text == "/quit":
            break
        if not text:
            continue
        delta = run_prompt_hook(session_id, text)
        if delta:
            print(f"  [profile] {delta.splitlines()[1].strip() if delta.count(chr(10)) else delta}")
        system = render(lib.load_profile())          # re-render every turn: the file may have changed
        if delta:
            system += "\n\n" + delta
        history.append({"role": "user", "content": text})
        r = client.chat.completions.create(model=args.model, reasoning_effort="low",
                                           messages=[{"role": "system", "content": system}, *history],
                                           max_completion_tokens=3000)
        reply = (r.choices[0].message.content or "").strip()
        history.append({"role": "assistant", "content": reply})
        print(f"\n{args.model}> {reply}\n")
        on_stop.process({"session_id": session_id, "last_assistant_message": reply})   # synchronous here
    with lib.locked():
        profile = lib.load_profile()
        changes = on_session_end.consolidate(profile, session_id)
        if changes:
            lib.save_profile(profile)
            lib.append_log(changes)
        lib.session_state_path(session_id).unlink(missing_ok=True)
    print(f"session end: {len(changes)} consolidation changes")


if __name__ == "__main__":
    main()
