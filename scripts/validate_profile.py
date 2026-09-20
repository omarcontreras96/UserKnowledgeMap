#!/usr/bin/env python3
"""Validate a profile against the skeleton. Usage: validate_profile.py [profile.json]"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

path = Path(sys.argv[1]) if len(sys.argv) > 1 else lib.profile_path()
profile = lib.load_profile(path)
problems = lib.validate(profile)
if problems:
    print(f"INVALID {path}:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
states = Counter(n["state"] for n in profile["nodes"].values())
gen = sum(1 for n in profile["nodes"].values() if n.get("source") == "generated")
print(f"ok {path}: {len(profile['nodes'])} nodes {dict(states)}, {gen} generated leaves")
