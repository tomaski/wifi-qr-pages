#!/bin/sh
# Unit tests for the parsing/naming/config logic (stdlib unittest, no extra deps).
set -eu

. "$(cd "$(dirname "$0")" && pwd)/env.sh"

[ -x "$VENV_PY" ] || {
    printf '\033[31mError:\033[0m .venv not found. Run ./setup.sh first.\n' >&2
    exit 1
}

export PYTHONPATH="$PROJECT_DIR/src"
cd "$PROJECT_DIR"
exec "$VENV_PY" -m unittest discover -s tests -v "$@"
