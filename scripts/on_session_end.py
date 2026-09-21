#!/usr/bin/env python3
"""SessionEnd hook: consolidate the profile after a session and clean up session state.

Rules (one level only; the tree is containment, not a curriculum, so we do not climb further):
  1. A parent with >= EXPOSE_AT descendants in state exposed/used becomes `exposed`
     (evidence names the concepts). An explicit `unknown` parent is allowed to become `exposed`:
     the user was, in fact, taught things in that area.
  2. A parent of a `used` leaf becomes `inferred` if it has no state yet. Inference never
     overrides evidence.
  3. Prerequisite inference where AL-CPL has edges (data/prereqs.json): a `used` leaf marks each
     missing direct prerequisite `inferred`, placed under the same parent.
Also deletes $BONSAI_HOME/session-<id>.json.

Manual test: echo '{"session_id":"t"}' | on_session_end.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

EXPOSE_AT = 3
PREREQS_PATH = lib.ROOT / "data" / "prereqs.json"


def load_prereqs() -> dict[str, list[str]]:
    if not PREREQS_PATH.exists():
        return {}
    return json.loads(PREREQS_PATH.read_text(encoding="utf-8")).get("prereqs", {})


def consolidate(profile: dict, session_id: str | None = None) -> list[dict]:
    nodes = profile.get("nodes", {})
    changes: list[dict] = []
    by_parent: dict[str, list[str]] = defaultdict(list)
    # Only conversation-derived leaves feed rules 1 and 2. Skeleton-level states come from the seed
    # or the user, and three seeded fields should not promote their whole discipline.
    for nid, n in list(nodes.items()):
        if n.get("state") in ("exposed", "used") and n.get("source") == "generated":
            p = lib.parent_of(nid, profile)
            if p:
                by_parent[p].append(nid)

    # rule 1: enough exposure below -> parent exposed
    for parent, kids in by_parent.items():
        if len(kids) >= EXPOSE_AT and nodes.get(parent, {}).get("state") not in ("exposed", "used"):
            names = ", ".join(lib.node_name(k, profile) for k in kids[:4])
            e = lib.transition(profile, parent, "exposed",
                               f"consolidation: {len(kids)} concepts explained here ({names})",
                               session=session_id)
            if e:
                changes.append(e)

    # rule 2: a used leaf -> parent inferred (only fills absence)
    for parent, kids in by_parent.items():
        used = [k for k in kids if nodes[k]["state"] == "used"]
        if used and parent not in nodes:
            e = lib.transition(profile, parent, "inferred",
                               f"consolidation: used {lib.node_name(used[0], profile)} correctly",
                               session=session_id)
            if e:
                changes.append(e)

    # rule 3: AL-CPL prerequisites of used leaves
    prereqs = load_prereqs()
    for nid, n in list(nodes.items()):
        if n.get("state") != "used":
            continue
        name = lib.node_name(nid, profile).lower()
        for pre in prereqs.get(name, []):
            if lib.find_by_name(pre, profile):
                continue
            parent = lib.parent_of(nid, profile) or "general"
            if parent == "general":
                lib.ensure_general(profile)
            e = lib.transition(profile, f"{parent}/{lib.slug(pre)}", "inferred",
                               f"consolidation: prerequisite of {lib.node_name(nid, profile)} (AL-CPL)",
                               name=pre, parent=parent, session=session_id)
            if e:
                changes.append(e)
    return changes


def main():
    if lib.disabled():
        return
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    session_id = payload.get("session_id")
    with lib.locked():
        profile = lib.load_profile()
        if not profile.get("nodes"):
            return
        changes = consolidate(profile, session_id)
        if changes:
            lib.save_profile(profile)
            lib.append_log(changes)
        if session_id:
            lib.session_state_path(session_id).unlink(missing_ok=True)
        # A detached Stop worker can recreate a session file after we delete it; sweep stale ones.
        cutoff = time.time() - 6 * 3600
        for p in lib.knowledge_home().glob("session-*.json"):
            if p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)
    lib.debug(f"on_session_end: {len(changes)} changes")
    if "--verbose" in sys.argv:
        for c in changes:
            print(f"{c['node']}: {c['from']} -> {c['to']}  ({c['evidence']})")


if __name__ == "__main__":
    main()
