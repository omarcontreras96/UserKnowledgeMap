#!/usr/bin/env python3
"""UserPromptSubmit hook: update the profile from what the user just typed, and tell the agent.

Reads the hook JSON on stdin ({session_id, user_input, ...}). Whatever is printed on stdout is added
to the model's context for this turn, so we print a one-line delta when something changed.

Signals, in priority order (a term captured by an earlier rule is not re-used by a later one):
  user-stated known    "I already know X", "I'm familiar with X", "you can assume X"  -> used
  user-stated unknown  "I don't know X", "I've never heard of X", "never learned X"   -> unknown
  asked                "what is X", "what's X again", "explain X", "I don't understand X" -> asked
  used                 a tracked concept name appears in a non-question context        -> used
Unresolvable X (not in skeleton or profile) becomes a generated leaf, placed under the subfield the
session was last talking about, else under a discipline chosen by a fast model call.

Usage for manual testing:  echo '{"session_id":"t","user_input":"what is torque?"}' | on_prompt.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ART = r"(?:the |a |an |some )?"
NOT_OBJ = r"(?!(?:in|this|that|it|how|why|what|more|again|briefly|shortly|simply|to|me|please|like|with|using)\b)"
TERM = r"(?P<term>[A-Za-z][A-Za-z0-9' \-]{1,60}?)"
TAIL = r"(?:\s+(?:again|exactly|though|here|there|really|actually|even|mean|means|is|are|was|were))*"
END = r"\s*(?:[?.!,;:]|$|\band\b|\bbut\b|\bso\b|\bbecause\b|\bor\b)"

KNOWN_PATTERNS = [
    rf"\bi(?:'m| am) (?:already |quite |very |pretty )?(?:familiar|comfortable) with {ART}{TERM}{END}",
    rf"\bi (?:already |do )?know (?:what |how |about )?{ART}{TERM}(?: is| are| works?| means?)?{END}",
    rf"\bi(?:'ve| have) (?:already )?(?:studied|taken|learned|learnt|done|covered) {ART}{TERM}{END}",
    rf"\byou can assume (?:i know |i understand |familiarity with )?{ART}{TERM}{END}",
    rf"\bi understand {ART}{TERM}(?: fine| well| already)?{END}",
]
UNKNOWN_PATTERNS = [
    rf"\bi (?:don't|do not|never) (?:know|knew) (?:what |how |anything about |much about )?{ART}{TERM}(?: is| are| works?| means?)?{END}",
    rf"\bi(?:'ve| have) never (?:heard of|learned|learnt|studied|taken|seen) {ART}{TERM}{END}",
    rf"\bnever (?:learned|learnt|studied|took|heard of) {ART}{TERM}{END}",
    rf"\b(?:i have |i've )?(?:got )?no (?:idea|clue) (?:what |about )?{ART}{TERM}(?: is| are| means?)?{END}",
]
ASKED_PATTERNS = [
    rf"\bwhat(?:'s| is| are| does| do) {ART}{NOT_OBJ}{TERM}{TAIL}{END}",
    rf"\bwhat do you mean by {ART}{TERM}{END}",
    rf"\b(?:can|could) you (?:please )?(?:explain|define|clarify) (?:what |how )?{ART}{NOT_OBJ}{TERM}(?: is| are| works?| means?)?(?: to me| for me| please)?{END}",
    rf"\b(?:explain|define) (?:what |how )?{ART}{NOT_OBJ}{TERM}(?: is| are| works?| means?)?(?: to me| for me| please)?{END}",
    rf"\bi (?:don't|do not) (?:really |quite )?(?:understand|get|follow) {ART}{TERM}{END}",
    rf"\b(?:remind me|refresh me on) (?:what |how )?{ART}{TERM}(?: is| are| works?| means?)?{END}",
]
STOPWORDS = {"it", "that", "this", "these", "those", "you", "me", "here", "there", "going on", "happening",
             "the point", "the difference", "the answer", "wrong", "next", "up", "going", "the deal",
             "your name", "time", "today", "the plan", "the idea"}
GENERIC_NAMES = {"business", "law", "history", "language", "analysis", "data", "religion", "design",
                 "education", "management", "strategy", "finance", "marketing", "geometry", "algebra",
                 "logic", "ethics", "medicine", "music", "art", "theatre", "dance", "physics", "chemistry",
                 "biology", "economics", "psychology", "sociology", "statistics", "philosophy", "engineering"}


NOT_A_CONCEPT = re.compile(
    r"^(?:the )?(?:difference|differences|point|purpose|reason|deal|best way|right way|relationship|"
    r"connection|link|problem|issue|matter|story|catch|takeaway|answer|result|plan|idea|status)\b")


def clean_term(t: str) -> str:
    t = t.strip(" \t'\"-").lower()
    t = re.sub(r"^(?:what |how |about )", "", t)
    t = re.sub(r"\s+(?:to me|for me|please)$", "", t)
    t = re.sub(r"\s+(?:is|are|was|were|means?|works?|again|exactly|though|here|there)$", "", t)
    return t.strip()


def strip_paren(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", name).strip() or name


def extract(patterns: list[str], text: str) -> list[str]:
    out = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            term = clean_term(m.group("term"))
            if (len(term) >= 3 and term not in STOPWORDS and term not in out
                    and len(term.split()) <= 5 and not NOT_A_CONCEPT.match(term)):
                out.append(term)
    return out


def tracked_names(profile: dict) -> dict[str, str]:
    """lowercase name -> node id, for 'used' detection. Profile nodes always; skeleton nodes only when
    the name is multi-word (single generic words like 'analysis' would be constant false positives)."""
    idx: dict[str, str] = {}
    sk = lib.load_skeleton()["nodes"]
    for nid, n in sk.items():
        name = n["name"].lower()
        if " " in name and name not in GENERIC_NAMES:
            idx[name] = nid
    for nid, n in profile.get("nodes", {}).items():
        idx[lib.node_name(nid, profile).lower()] = nid
        for a in n.get("aliases", []):
            idx[a.lower()] = nid
    return idx


def stem_pattern(name: str) -> str:
    """Regex that matches inflections of each word: 'precession' also hits 'precess', 'precessing';
    'torque' hits 'torques', 'torqued'. Words under 5 letters are matched exactly."""
    parts = []
    for w in re.split(r"[\s\-]+", name.lower()):
        if len(w) >= 5:
            stem = re.sub(r"(?:ation|ition|ssion|sion|tion|ing|ies|es|ed|s|y)$", "", w)
            stem = stem if len(stem) >= 4 else w
            parts.append(re.escape(stem) + r"[a-z]{0,5}")
        else:
            parts.append(re.escape(w))
    return r"(?<![a-z0-9])" + r"[\s\-]+".join(parts) + r"(?![a-z0-9])"


def find_used(text: str, profile: dict, exclude: set[str]) -> list[tuple[str, str]]:
    low = text.lower()
    hits = []
    for name, nid in tracked_names(profile).items():
        if name in exclude or len(name) < 4 or name in GENERIC_NAMES:
            continue
        if re.search(stem_pattern(name), low):
            hits.append((name, nid))
    return hits


def confirm_used(text: str, names: list[str]) -> list[str]:
    """Ask the fast model which of `names` the user actually used correctly (not just mentioned)."""
    res = lib.chat_json(
        "You judge whether a user employed technical concepts correctly in their own words. "
        "Return JSON {\"used_correctly\": [names]} listing only the concepts the message uses in a way "
        "that shows understanding (applies it, reasons with it). A bare mention, a question about it, or "
        "a quote of someone else's words does not count.",
        json.dumps({"message": text, "concepts": names}), timeout=6.0, max_tokens=200)
    if not res:
        return names  # model unavailable: accept, noisy on purpose
    return [n for n in res.get("used_correctly", []) if n in names]


def place_new_concept(term: str, session: dict) -> tuple[str, str] | None:
    """Return (parent_id, display_name) for a concept not in the skeleton, or None if the model says
    the phrase is not a discrete concept (a comparison, a task, a question)."""
    res = lib.chat_json(
        "You place concepts in an academic taxonomy. Return JSON {\"is_concept\": bool, "
        "\"discipline\": <one of the given ids>, \"field\": <short name of the most specific field it "
        "belongs to>, \"name\": <short canonical name, 1-4 words, no parentheses>}. is_concept is false "
        "when the phrase is a comparison, a task, an opinion, or otherwise not a nameable concept.",
        json.dumps({"concept": term, "disciplines": lib.disciplines()}), timeout=6.0, max_tokens=150)
    if res is None:
        return lib.place_under(None, None, session), term[:1].upper() + term[1:]
    if not res.get("is_concept", True):
        return None
    name = strip_paren(res.get("name") or term)
    name = name[:1].upper() + name[1:]
    return lib.place_under(res.get("discipline"), res.get("field"), session), name


def resolve_or_create(term: str, profile: dict, session: dict):
    """-> (node_id, name_for_new_leaf or None, parent_for_new_leaf or None), or None to skip."""
    nid = lib.find_by_name(term, profile)
    if nid:
        return nid, None, None
    placed = place_new_concept(term, session)
    if placed is None:
        return None
    parent, name = placed
    existing = lib.find_by_name(name, profile)      # the canonical name may already be a node
    if existing:
        profile["nodes"].get(existing, {}).setdefault("aliases", [])
        if existing in profile["nodes"] and term.lower() != name.lower():
            profile["nodes"][existing]["aliases"].append(term)
        return existing, None, None
    if parent == "general":
        lib.ensure_general(profile)
    return f"{parent}/{lib.slug(name)}", name, parent


def main():
    if lib.disabled():
        return
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    text = (payload.get("user_input") or payload.get("prompt") or "").strip()
    session_id = payload.get("session_id", "nosession")
    if len(text) < 4:
        return

    with lib.locked():
        _run(text, session_id)


def _run(text: str, session_id: str) -> None:
    profile = lib.load_profile()
    session = lib.load_session_state(session_id)
    changes: list[dict] = []
    captured: set[str] = set()

    def apply(term, state, evidence, user_stated=False):
        resolved = resolve_or_create(term, profile, session)
        captured.add(term)
        if resolved is None:
            return
        nid, name, parent = resolved
        entry = lib.transition(profile, nid, state, evidence, name=name, parent=parent,
                               user_stated=user_stated, session=session_id)
        node = profile["nodes"].get(nid)
        if node is not None and name and term.lower() != name.lower():
            node.setdefault("aliases", [])
            if term not in node["aliases"]:
                node["aliases"].append(term)
        captured.add(lib.node_name(nid, profile).lower())
        if entry:
            changes.append(entry)

    for term in extract(KNOWN_PATTERNS, text):
        apply(term, "used", f"user said they know it: \"{text[:80]}\"", user_stated=True)
    for term in extract(UNKNOWN_PATTERNS, text):
        if term not in captured:
            apply(term, "unknown", f"user said they don't know it: \"{text[:80]}\"", user_stated=True)
    for term in extract(ASKED_PATTERNS, text):
        if term not in captured:
            apply(term, "asked", f"user asked: \"{text[:80]}\"")

    used_hits = [(n, i) for n, i in find_used(text, profile, captured)]
    if used_hits:
        names = [n for n, _ in used_hits]
        ok = set(confirm_used(text, names)) if len(text) > 25 else set(names)
        for name, nid in used_hits:
            if name in ok:
                entry = lib.transition(profile, nid, "used", f"user used it: \"{text[:80]}\"", session=session_id)
                if entry:
                    changes.append(entry)

    session["turns"] = session.get("turns", 0) + 1
    lib.save_session_state(session_id, session)
    if not changes:
        return
    lib.save_profile(profile)
    lib.append_log(changes)

    lines = ["Knowledge profile update (from the user's last message):"]
    for c in changes:
        if c["from"] == c["to"]:
            was = " (confirmed by the user)"
        else:
            was = f" (was: {c['from']})" if c["from"] else ""
        hint = {"asked": "explain it from scratch, from concepts they know.",
                "used": "assume fluency.",
                "unknown": "do not assume it; introduce it from concepts they know if needed.",
                }.get(c["to"], "")
        lines.append(f"- \"{c['name']}\" -> {c['to']}{was}. {hint}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
