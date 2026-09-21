#!/usr/bin/env python3
"""Stop hook: record the concepts the agent just explained as `exposed`.

Claude Code runs this after every assistant turn with {session_id, last_assistant_message, ...} on
stdin. Stop hooks block the turn until they exit, so this script hands the work to a detached worker
process and exits immediately. The worker makes one fast-model call, updates the profile under the
lock, and remembers the turn's topic in the session state so on_prompt.py can place follow-up
questions ("what's torque?") under the right subfield without a second placement call.

Manual test:   echo '{"session_id":"t","last_assistant_message":"..."}' | on_stop.py --sync
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

MIN_CHARS = 300          # shorter replies are acknowledgements or tool chatter, not explanations
MAX_CONCEPTS = 5

SYSTEM = """You read one reply from an AI assistant and list the concepts it EXPLAINED to the user:
concepts it defined, taught, or introduced with a description. Do not list concepts that are merely
mentioned in passing or assumed, and do not list the topic of the user's question unless the reply
explains it. Use names that would appear as a textbook index entry (1-3 words, no parentheses,
no invented compounds): "Torque", "Precession", "Angular momentum", not "Frictional spin decay".
Skip concepts that have no standard name. At most %d concepts.
Return JSON:
{"explained": [{"name": str, "discipline": <one of the given discipline ids>, "field": <short name of
the most specific field>}], "topic_discipline": <discipline id the reply is mostly about, or null>}
If the reply explains nothing (code, a list of files, small talk), return {"explained": []}.""" % MAX_CONCEPTS


BAD_NAME = re.compile(r"\b(?:and|or|from|vs|versus|relation|relationship|between|effect of|role of)\b", re.I)


def acceptable_name(name: str) -> bool:
    """Textbook-index names only: 1-3 words, no conjunction-style compounds."""
    return 3 <= len(name) <= 40 and len(name.split()) <= 3 and not BAD_NAME.search(name) and "(" not in name


def looks_like_prose(text: str) -> bool:
    if len(text) < MIN_CHARS:
        return False
    code_lines = sum(1 for l in text.splitlines() if l.startswith(("    ", "\t", "```", "$ ", "- [")))
    return code_lines < max(3, len(text.splitlines()) // 2)


def process(payload: dict) -> list[dict]:
    text = payload.get("last_assistant_message") or ""
    session_id = payload.get("session_id", "nosession")
    if not looks_like_prose(text):
        return []
    with lib.locked():
        profile = lib.load_profile()
        session = lib.load_session_state(session_id)
    tracked = sorted({lib.node_name(n, profile) for n in profile["nodes"]})[:120]
    res = lib.chat_json(
        SYSTEM,
        json.dumps({"reply": text[:6000], "disciplines": lib.disciplines(),
                    "already_tracked_names": tracked}),
        timeout=25.0, max_tokens=1200, reasoning="low")   # detached, so a few extra seconds are free
    if not res:
        return []
    changes, parents = [], []
    with lib.locked():
        profile = lib.load_profile()
        session = lib.load_session_state(session_id)
        for item in res.get("explained", [])[:MAX_CONCEPTS]:
            name = (item.get("name") or "").strip()
            if not acceptable_name(name):
                continue
            nid = lib.find_by_name(name, profile)
            new_name = new_parent = None
            if nid is None:
                parent = lib.place_under(item.get("discipline"), item.get("field"), session)
                if parent == "general":
                    lib.ensure_general(profile)
                nid, new_name, new_parent = f"{parent}/{lib.slug(name)}", name, parent
            entry = lib.transition(profile, nid, "exposed", f"agent explained it (turn {session.get('turns', 0)})",
                                   name=new_name, parent=new_parent, session=session_id)
            if entry:
                changes.append(entry)
            p = lib.parent_of(nid, profile)
            if p and p not in parents:
                parents.append(p)
        if parents:
            session["last_parents"] = (parents + [x for x in session.get("last_parents", []) if x not in parents])[:3]
        elif res.get("topic_discipline") in lib.disciplines():
            session["last_parents"] = [res["topic_discipline"]]
        lib.save_session_state(session_id, session)
        if changes:
            lib.save_profile(profile)
            lib.append_log(changes)
    lib.debug(f"on_stop: {len(changes)} exposed, parents={parents}")
    return changes


def main():
    if "--worker" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--worker") + 1])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            process(payload)
        except Exception as e:  # noqa: BLE001
            lib.debug(f"on_stop worker failed: {type(e).__name__}: {e}")
        finally:
            path.unlink(missing_ok=True)
        return
    if lib.disabled():
        return
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if payload.get("stop_hook_active"):
        return
    if "--sync" in sys.argv:
        for c in process(payload):
            print(f"{c['node']}: {c['from']} -> {c['to']}")
        return
    if not looks_like_prose(payload.get("last_assistant_message") or ""):
        return
    fd, tmp = tempfile.mkstemp(prefix="bonsai-stop-", suffix=".json", dir=str(lib.knowledge_home()))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    subprocess.Popen([sys.executable, __file__, "--worker", tmp], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True)


if __name__ == "__main__":
    main()
