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


def load_env() -> None:
    """Load KEY=VALUE lines from $KNOWLEDGE_HOME/.env and <repo>/.env into os.environ (no override)."""
    for p in (knowledge_home() / ".env", ROOT / ".env"):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


# Model ids used by hooks and eval. Override with env vars of the same name.
load_env()
MODEL_FAST = os.environ.get("UKM_MODEL_FAST", "gpt-5-mini")     # inside hooks: latency matters
MODEL_GEN = os.environ.get("UKM_MODEL_GEN", "gpt-5")            # eval: answer generation
MODEL_JUDGE = os.environ.get("UKM_MODEL_JUDGE", "gpt-5")        # eval: judge


def openai_client(timeout: float = 20.0):
    """Lazy OpenAI client; raises a clear error if the key is missing."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set; put it in ~/.knowledge/.env (see README)")
    from openai import OpenAI
    return OpenAI(timeout=timeout, max_retries=0)


def chat_json(system: str, user: str, *, model: str | None = None, timeout: float = 8.0,
              max_tokens: int = 600) -> dict | None:
    """One fast JSON-mode call. Returns the parsed object, or None on any failure (hooks must not break)."""
    try:
        c = openai_client(timeout=timeout)
        r = c.chat.completions.create(
            model=model or MODEL_FAST, reasoning_effort="minimal",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_completion_tokens=max_tokens,
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as e:  # noqa: BLE001
        debug(f"chat_json failed: {type(e).__name__}: {e}")
        return None


def debug(msg: str) -> None:
    """Append to $KNOWLEDGE_HOME/debug.log (hooks cannot print diagnostics to the user)."""
    try:
        with (knowledge_home() / "debug.log").open("a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
    except OSError:
        pass


def session_state_path(session_id: str) -> Path:
    return knowledge_home() / f"session-{session_id}.json"


def load_session_state(session_id: str) -> dict:
    p = session_state_path(session_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"last_parents": [], "turns": 0}


def save_session_state(session_id: str, state: dict) -> None:
    session_state_path(session_id).write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


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
            if n.get("name", "").lower() == key or key in [a.lower() for a in n.get("aliases", [])]:
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
            # User statements are sticky against contradiction by weak automatic evidence,
            # but not against progress: "I don't know X" -> explained -> exposed is fine.
            if new_state == "inferred":
                return None
            if old_state == "used" and new_state in ("asked", "exposed", "unknown"):
                return None
            if old_state == "unknown" and new_state == "unknown":
                return None
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
