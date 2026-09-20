#!/usr/bin/env python3
"""Fetch the AL-CPL concept-prerequisite dataset and write data/prereqs.json.

AL-CPL (Liang et al., 2018; built on Wang et al., 2016), CC BY-NC-SA 4.0,
https://github.com/harrylclc/AL-CPL-dataset. Four domains: data mining, geometry, physics,
precalculus. The published edges include the transitive closure; we keep only direct edges
(transitive reduction) so "Random forest" points at bagging and decision trees, not at arithmetic mean.

Output: {"<concept name, lowercase>": ["<prerequisite name>", ...]} with Wikipedia underscores as spaces.
"""
import csv
import io
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prereqs.json"
BASE = "https://raw.githubusercontent.com/harrylclc/AL-CPL-dataset/master/data/"
DOMAINS = ["physics", "geometry", "precalculus", "data_mining"]
GENERIC = {"physics", "mathematics", "geometry", "data mining", "statistics", "algebra", "calculus",
           "precalculus", "science", "machine learning"}


def pretty(t: str) -> str:
    return t.replace("_", " ").strip()


def main():
    edges: dict[str, set[str]] = defaultdict(set)   # concept -> prerequisites (closure)
    for d in DOMAINS:
        with urllib.request.urlopen(BASE + f"{d}.preqs", timeout=30) as r:
            for a, b in csv.reader(io.StringIO(r.read().decode("utf-8"))):
                a, b = pretty(a), pretty(b)
                if b.lower() in GENERIC or a == b:
                    continue
                edges[a].add(b)
    # transitive reduction: drop (a, c) when some b has (a, b) and (b, c)
    direct: dict[str, list[str]] = {}
    for a, pre in edges.items():
        keep = {c for c in pre if not any(c in edges.get(b, ()) for b in pre if b != c)}
        direct[a.lower()] = sorted(keep)
    OUT.write_text(json.dumps({"source": "AL-CPL (Liang et al. 2018), CC BY-NC-SA 4.0, transitive reduction",
                               "prereqs": direct}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    n_edges = sum(len(v) for v in direct.values())
    print(f"wrote {OUT.relative_to(ROOT)}: {len(direct)} concepts, {n_edges} direct edges "
          f"(from {sum(len(v) for v in edges.values())} closure edges)")
    for k in ("torque", "friction", "random forest", "derivative"):
        print(f"  {k}: {direct.get(k)}")


if __name__ == "__main__":
    main()
