#!/usr/bin/env bash
# Reset $BONSAI_HOME (default ~/.bonsai) to the persona seed and clear the log.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${BONSAI_HOME:-$HOME/.bonsai}"
PERSONA="${1:-mba}"
mkdir -p "$HOME_DIR"
cp "$ROOT/data/profile.persona-$PERSONA.json" "$HOME_DIR/profile.json"
: > "$HOME_DIR/log.jsonl"
rm -f "$HOME_DIR"/session-*.json
python3 "$ROOT/scripts/validate_profile.py" "$HOME_DIR/profile.json"
echo "reset $HOME_DIR to persona '$PERSONA'"
