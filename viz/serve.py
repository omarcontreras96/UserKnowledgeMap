#!/usr/bin/env python3
"""Serve the tree visualization plus live JSON of the profile and log.

    python3 viz/serve.py            # http://localhost:8766
    KNOWLEDGE_HOME=... python3 viz/serve.py --port 9000

Endpoints: /  (index.html), /api/skeleton, /api/profile, /api/log?n=50, /api/reset (POST; re-seeds
the demo persona), /api/state (profile + log in one call, what the page polls).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import lib  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "viz"), **kw)

    def log_message(self, *args):  # quiet
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/skeleton":
            return self.send_json(lib.load_skeleton())
        if u.path == "/api/profile":
            return self.send_json(lib.load_profile())
        if u.path == "/api/log":
            n = int(parse_qs(u.query).get("n", ["50"])[0])
            return self.send_json(lib.read_log(n))
        if u.path == "/api/state":
            n = int(parse_qs(u.query).get("n", ["60"])[0])
            return self.send_json({"profile": lib.load_profile(), "log": lib.read_log(n),
                                   "home": str(lib.knowledge_home())})
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/reset":
            r = subprocess.run([str(ROOT / "scripts" / "reset_demo.sh")], capture_output=True, text=True)
            return self.send_json({"ok": r.returncode == 0, "out": r.stdout + r.stderr})
        self.send_json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"knowledge map at http://localhost:{args.port}  (profile: {lib.profile_path()})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
