#!/usr/bin/env python3
"""Build data/skeleton.json from Wikipedia's "Outline of academic disciplines".

Three levels: discipline -> field -> subfield. Deeper bullets are dropped.
The five branches (Humanities, Social science, ...) are kept as a label on each discipline.

Usage:
    python3 scripts/build_skeleton.py            # uses cached data/outline.wikitext if present
    python3 scripts/build_skeleton.py --refetch  # re-download from the MediaWiki API
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "outline.wikitext"
OUT = ROOT / "data" / "skeleton.json"
PAGE = "Outline_of_academic_disciplines"
API = "https://en.wikipedia.org/w/api.php"

# Subtrees that are not knowledge areas in any useful sense for this project.
# Matched against the Wikipedia title of a field/subfield; the node and its children are dropped.
DROP_TITLES = {
    "Space colonization", "Space commercialization", "Space-based economy", "Space industry",
    "Space manufacturing", "Space tourism", "Space food", "Space logistics", "Religion in space",
    "Sex in space", "Space and survival", "Space warfare", "Writing in space", "Space corrosion",
    "Neuroscience in space", "Space architecture", "Space environment", "Space medicine",
}
# H3 sections that are not disciplines.
SKIP_H3 = {"Interdisciplinary studies"}


def fetch() -> str:
    q = urllib.parse.urlencode({
        "action": "parse", "page": PAGE, "prop": "wikitext", "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "bonsai/0.1 (hackathon)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["parse"]["wikitext"]


def slug(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")


def first_link(text: str):
    """Return (wiki_title, display_name) of the first wikilink, ignoring '(outline)' helper links."""
    for m in LINK.finditer(text):
        title = m.group(1).strip()
        if title.lower().startswith("outline of"):
            continue
        display = (m.group(2) or title).strip()
        return title, display
    return None


def clean_heading(line: str) -> str:
    return re.sub(r"=+", "", line).strip()


def walk(wikitext: str):
    """Yield ('branch', name) | ('discipline', title, group) | ('item', depth, name, wiki_title)."""
    lines = wikitext.split("\n")
    stop = next((i for i, l in enumerate(lines) if l.startswith("== See also")), len(lines))
    h3_title = None
    for raw in lines[:stop]:
        line = re.sub(r"\{\{.*?\}\}", "", raw).rstrip()
        if not line.strip():
            continue
        if line.startswith("===="):
            yield ("discipline", clean_heading(line), h3_title)
        elif line.startswith("==="):
            h3_title = clean_heading(line)
            if h3_title not in SKIP_H3:
                yield ("discipline", h3_title, None)
            else:
                yield ("discipline", None, None)
        elif line.startswith("=="):
            h3_title = None
            yield ("branch", clean_heading(line))
        else:
            m = re.match(r"^(\*+)\s*(.*)$", line)
            if not m:
                continue
            depth = len(m.group(1))
            if depth > 2:
                continue
            link = first_link(m.group(2))
            if link:
                wiki_title, name = link
            else:
                name = re.sub(r"'+", "", m.group(2)).strip()
                wiki_title = name
            if name:
                yield ("item", depth, name, wiki_title)


def parse(wikitext: str):
    events = list(walk(wikitext))

    # Pass 1: choose one placement per title: shallowest depth wins, then first seen.
    chosen: dict[str, tuple[int, int]] = {}
    for idx, ev in enumerate(events):
        if ev[0] == "item":
            depth, wiki_title = ev[1], ev[3]
            if wiki_title not in chosen or depth < chosen[wiki_title][0]:
                chosen[wiki_title] = (depth, idx)

    # Pass 2: build the tree.
    nodes: dict[str, dict] = {}
    children: dict[str, list[str]] = {}
    by_title: dict[str, str] = {}
    dropped = 0
    branch = None
    discipline_id = None
    field_id = None          # id of the current depth-1 item's node (None if not placed here)
    field_dropped = False

    def add(node_id, **kw):
        nodes[node_id] = kw
        children.setdefault(node_id, [])
        if kw.get("parent"):
            children[kw["parent"]].append(node_id)
        by_title[kw["wiki_title"]] = node_id

    for idx, ev in enumerate(events):
        if ev[0] == "branch":
            branch = ev[1]
            discipline_id = field_id = None
        elif ev[0] == "discipline":
            title, group = ev[1], ev[2]
            field_id = None
            if title is None:
                discipline_id = None
                continue
            discipline_id = slug(title)
            add(discipline_id, name=title, level="discipline", parent=None, branch=branch,
                group=group, wiki_title=title)
        else:
            _, depth, name, wiki_title = ev
            if discipline_id is None:
                continue
            if wiki_title in DROP_TITLES:
                dropped += 1
                if depth == 1:
                    field_dropped, field_id = True, None
                continue
            placed_here = chosen[wiki_title][1] == idx
            if depth == 1:
                field_dropped = False
                if placed_here:
                    node_id = f"{discipline_id}/{slug(name)}"
                    add(node_id, name=name, level="field", parent=discipline_id, branch=branch,
                        wiki_title=wiki_title)
                    field_id = node_id
                else:
                    existing = by_title.get(wiki_title)
                    if existing:
                        nodes[existing].setdefault("also_under", []).append(discipline_id)
                    # subfields listed here attach to the chosen copy if it already exists
                    field_id = existing if existing and nodes[existing]["level"] == "field" else None
            else:
                if field_id is None or field_dropped:
                    continue
                if placed_here:
                    node_id = f"{field_id}/{slug(name)}"
                    add(node_id, name=name, level="subfield", parent=field_id, branch=branch,
                        wiki_title=wiki_title)
                else:
                    existing = by_title.get(wiki_title)
                    if existing:
                        nodes[existing].setdefault("also_under", []).append(field_id)

    # An H3 that turned out to contain H4s is a group label, not a discipline: remove it.
    for nid in list(nodes):
        n = nodes[nid]
        if n["level"] == "discipline" and n.get("group") is None and not children[nid]:
            if any(m.get("group") == n["name"] for m in nodes.values()):
                del nodes[nid]
                del children[nid]
                by_title.pop(n["wiki_title"], None)

    return nodes, children, dropped


def main():
    if "--refetch" in sys.argv or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(fetch(), encoding="utf-8")
        print(f"fetched {RAW.name} ({RAW.stat().st_size} bytes)")
    nodes, children, dropped = parse(RAW.read_text(encoding="utf-8"))
    counts = {}
    for n in nodes.values():
        counts[n["level"]] = counts.get(n["level"], 0) + 1
    out = {
        "source": f"https://en.wikipedia.org/wiki/{PAGE}",
        "license": "CC BY-SA 4.0",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "levels": ["discipline", "field", "subfield"],
        "counts": counts,
        "nodes": nodes,
        "children": children,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {counts}  (dropped {dropped} junk items)")
    for nid, n in nodes.items():
        if n["level"] == "discipline":
            nf = len(children[nid])
            ns = sum(len(children[c]) for c in children[nid])
            print(f"  {n['branch']:<16} {n['name']:<45} fields={nf:<3} subfields={ns}")


if __name__ == "__main__":
    main()
