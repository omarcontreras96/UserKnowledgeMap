#!/usr/bin/env bash
# Run a hook script with the project venv if it exists, else the system python3.
# The hooks that call a model degrade gracefully without the `openai` package (they just record less).
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${UKM_PYTHON:-$HOME/.venvs/ukm/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"
exec "$PY" "$HERE/$1"
