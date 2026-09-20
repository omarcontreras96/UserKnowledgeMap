#!/usr/bin/env python3
"""Render the user's knowledge profile as a compact context block for an agent.

Used as a Claude Code SessionStart hook: whatever this prints on stdout enters the model's context.
Also importable: render(profile) -> str, used by the eval (condition C).

Usage: render_context.py [--profile PATH] [--max N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

MAX_PER_LIST = 25
RECENT_ASKED_WINDOW = 40  # log entries scanned for recent "asked" transitions

RULES = """How to explain things to this user:
1. Before answering, silently list the concepts your explanation rests on.
2. For each one that is not in KNOWS WELL: either replace it with something the user already knows
   (analogies from KNOWS WELL areas are welcome), or introduce it explicitly, defined only from
   concepts the user knows.
3. Introduce at most two new concepts per answer. Never use a third unknown concept to define the
   second. If the question genuinely needs more, teach the first two and say what comes next.
4. Do not simplify areas in KNOWS WELL; assume full fluency there.
5. Areas not listed: use your judgment, leaning toward rule 2.
6. If the user says they already know, or do not know, something, believe them; the profile will
   be updated automatically.
Keep this profile out of your replies unless the user asks about it."""


def label(node_id: str, profile: dict, incl: list[str] | None = None) -> str:
    """Display name qualified by discipline ('Analysis (Pure mathematics)'), unless the name already
    says it ('Microeconomics'). `incl` lists notable children hidden by roll-up."""
    names = lib.path_names(node_id, profile)
    name, disc = names[-1], names[0]
    qualify = len(names) >= 2 and disc.split()[-1].lower().rstrip("s") not in name.lower()
    parts = []
    if qualify:
        parts.append(disc)
    if incl:
        parts.append("incl. " + ", ".join(incl))
    return f"{name} ({'; '.join(parts)})" if parts else name


def rolled_up(profile: dict, state: str) -> list[tuple[str, list[str]]]:
    """(node_id, hidden_child_names) for nodes in `state` whose no ancestor is in the same state.
    An ancestor in the same state stands for its descendants; generated leaves it hides are named."""
    nodes = profile.get("nodes", {})
    ids = [nid for nid, n in nodes.items() if n.get("state") == state]
    hidden: dict[str, list[str]] = {}
    out = []
    for nid in ids:
        cur, top = lib.parent_of(nid, profile), None
        while cur:
            if nodes.get(cur, {}).get("state") == state:
                top = cur
            cur = lib.parent_of(cur, profile)
        if top is None:
            out.append(nid)
        elif nodes[nid].get("source") == "generated":
            hidden.setdefault(top, []).append(lib.node_name(nid, profile))
    # most recently updated first, so a capped list keeps what matters now
    out.sort(key=lambda i: nodes[i].get("updated_at", ""), reverse=True)
    return [(i, hidden.get(i, [])[:3]) for i in out]


def fmt_list(items, profile: dict, cap: int = MAX_PER_LIST) -> str:
    if not items:
        return "(none recorded)"
    items = [(i, []) if isinstance(i, str) else i for i in items]
    shown = [label(i, profile, incl) for i, incl in items[:cap]]
    extra = len(items) - cap
    return ", ".join(shown) + (f", +{extra} more" if extra > 0 else "")


def recent_asked(profile: dict) -> list[str]:
    seen, out = set(), []
    for e in reversed(lib.read_log(RECENT_ASKED_WINDOW)):
        if e.get("to") == "asked" and e["node"] not in seen:
            seen.add(e["node"])
            out.append(e["node"])
    for nid, n in profile.get("nodes", {}).items():
        if n.get("state") == "asked" and nid not in seen:
            seen.add(nid)
            out.append(nid)
    return out


def render(profile: dict, cap: int = MAX_PER_LIST) -> str:
    lines = ["<knowledge-profile>",
             "This user's knowledge map, maintained by the user and updated from past conversations. "
             "Treat it as ground truth about what they know."]
    if profile.get("bio"):
        lines.append(f"Background: {profile['bio']}")
    lines.append(f"KNOWS WELL: {fmt_list(rolled_up(profile, 'used'), profile, cap)}")
    lines.append(f"HAS SEEN BUT MAY NOT RECALL: {fmt_list(rolled_up(profile, 'exposed'), profile, cap)}")
    inferred = rolled_up(profile, "inferred")
    if inferred:
        lines.append(f"PROBABLY FAMILIAR (inferred, unconfirmed): {fmt_list(inferred, profile, cap)}")
    lines.append(f"DOES NOT KNOW: {fmt_list(rolled_up(profile, 'unknown'), profile, cap)}")
    asked = recent_asked(profile)
    if asked:
        lines.append("RECENTLY ASKED ABOUT (an earlier explanation did not land; explain from scratch if it "
                     f"comes up again): {fmt_list(asked, profile, cap)}")
    lines.append("")
    lines.append(RULES)
    lines.append("</knowledge-profile>")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=Path, default=None)
    ap.add_argument("--max", type=int, default=MAX_PER_LIST)
    args = ap.parse_args()
    profile = lib.load_profile(args.profile)
    if not profile.get("nodes"):
        return  # no profile yet: print nothing, add nothing to context
    print(render(profile, args.max))


if __name__ == "__main__":
    main()
