"""Shared helpers: paths, skeleton/profile IO, state transitions, validation.

Profile node states (strength order):  unknown < exposed < used
Side states:  asked    (user asked "what is X"; evidence an explanation did not land)
              inferred (set by parent/prerequisite inference, never by direct evidence)
Absence from profile["nodes"] means "no data", which is different from "unknown".

Precedence when transitions conflict:
  user-stated evidence  >  direct evidence (asked, used, exposed)  >  inferred
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKELETON_PATH = ROOT / "data" / "skeleton.json"

STATES = ("unknown", "exposed", "used", "asked", "inferred")
STRENGTH = {"unknown": 0, "inferred": 0.5, "asked": 0.75, "exposed": 1, "used": 2}
USER_STATED = "user-stated"


def knowledge_home() -> Path:
    p = Path(os.environ.get("KNOWLEDGE_HOME", Path.home() / ".knowledge")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def profile_path() -> Path:
    return knowledge_home() / "profile.json"


def log_path() -> Path:
    return knowledge_home() / "log.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(s: str) -> str:
    s = s.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ---------------------------------------------------------------- IO

_skeleton_cache: dict | None = None


def load_skeleton() -> dict:
    global _skeleton_cache
    if _skeleton_cache is None:
        _skeleton_cache = json.loads(SKELETON_PATH.read_text(encoding="utf-8"))
    return _skeleton_cache


def empty_profile(owner: str = "me", bio: str = "") -> dict:
    return {"version": 1, "owner": owner, "bio": bio, "created_at": now(), "nodes": {}}


def load_profile(path: Path | None = None) -> dict:
    path = path or profile_path()
    if not path.exists():
        return empty_profile()
    return json.loads(path.read_text(encoding="utf-8"))


def save_profile(profile: dict, path: Path | None = None) -> None:
    path = path or profile_path()
    path.write_text(json.dumps(profile, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def append_log(entries: list[dict]) -> None:
    if not entries:
        return
    with log_path().open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def read_log(limit: int | None = None) -> list[dict]:
    p = log_path()
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    if limit:
        lines = lines[-limit:]
    return [json.loads(l) for l in lines if l.strip()]


# ---------------------------------------------------------------- names and lookup

def node_name(node_id: str, profile: dict | None = None) -> str:
    sk = load_skeleton()["nodes"]
    if node_id in sk:
        return sk[node_id]["name"]
    if profile and node_id in profile["nodes"] and profile["nodes"][node_id].get("name"):
        return profile["nodes"][node_id]["name"]
    return node_id.rsplit("/", 1)[-1].replace("-", " ").capitalize()


def parent_of(node_id: str, profile: dict | None = None) -> str | None:
    sk = load_skeleton()["nodes"]
    if node_id in sk:
        return sk[node_id]["parent"]
    if profile and node_id in profile["nodes"]:
        return profile["nodes"][node_id].get("parent")
    return node_id.rsplit("/", 1)[0] if "/" in node_id else None


def path_names(node_id: str, profile: dict | None = None) -> list[str]:
    out, cur = [], node_id
    while cur:
        out.append(node_name(cur, profile))
        cur = parent_of(cur, profile)
    return list(reversed(out))


def find_by_name(name: str, profile: dict | None = None) -> str | None:
    """Case-insensitive lookup by display name or wiki title across skeleton + profile leaves."""
    key = name.strip().lower()
    if not key:
        return None
    sk = load_skeleton()["nodes"]
    for nid, n in sk.items():
        if n["name"].lower() == key or n.get("wiki_title", "").lower() == key:
            return nid
    if profile:
        for nid, n in profile["nodes"].items():
            if n.get("name", "").lower() == key:
                return nid
    # loose match: slug equality on the last path segment
    s = slug(name)
    for nid in list(sk) + (list(profile["nodes"]) if profile else []):
        if nid.rsplit("/", 1)[-1] == s:
            return nid
    return None


# ---------------------------------------------------------------- validation

def validate(profile: dict) -> list[str]:
    """Return a list of problems; empty means valid."""
    sk = load_skeleton()["nodes"]
    problems = []
    for nid, n in profile.get("nodes", {}).items():
        if n.get("state") not in STATES:
            problems.append(f"{nid}: bad state {n.get('state')!r}")
        if nid in sk:
            continue
        if n.get("source") != "generated":
            problems.append(f"{nid}: not in skeleton and not marked source=generated")
            continue
        parent = n.get("parent") or (nid.rsplit("/", 1)[0] if "/" in nid else None)
        if not parent or (parent not in sk and parent not in profile["nodes"]):
            problems.append(f"{nid}: generated leaf with unknown parent {parent!r}")
        if not n.get("name"):
            problems.append(f"{nid}: generated leaf needs a name")
    return problems


# ---------------------------------------------------------------- transitions

def transition(profile: dict, node_id: str, new_state: str, evidence: str, *,
               name: str | None = None, parent: str | None = None,
               user_stated: bool = False, session: str | None = None) -> dict | None:
    """Apply a state change under the precedence rules. Returns a log entry, or None if no change."""
    assert new_state in STATES, new_state
    nodes = profile.setdefault("nodes", {})
    cur = nodes.get(node_id)
    old_state = cur["state"] if cur else None
    cur_user_stated = bool(cur and cur.get("evidence", "").startswith(USER_STATED))

    if cur:
        if cur_user_stated and not user_stated:
            return None                                   # user statements are sticky
        if new_state == "inferred" and old_state not in (None, "inferred"):
            return None                                   # inference never overrides evidence
        if new_state == "exposed" and old_state == "used":
            return None                                   # already stronger
        if new_state == old_state and not user_stated:
            return None

    sk = load_skeleton()["nodes"]
    entry = cur or {}
    entry["state"] = new_state
    entry["evidence"] = (f"{USER_STATED}: {evidence}" if user_stated else evidence)
    entry["updated_at"] = now()
    if node_id not in sk:
        entry["source"] = "generated"
        entry["name"] = name or entry.get("name") or node_name(node_id)
        entry["parent"] = parent or entry.get("parent") or (node_id.rsplit("/", 1)[0] if "/" in node_id else None)
    nodes[node_id] = entry
    return {
        "ts": entry["updated_at"], "node": node_id, "name": node_name(node_id, profile),
        "from": old_state, "to": new_state, "evidence": entry["evidence"], "session": session,
    }
