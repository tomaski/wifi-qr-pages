#!/bin/sh
# Shared environment for wifi-qr-pages. Sourced by setup.sh and the ./qrpages launcher.
#
# Every cache/state directory that the toolchain would otherwise place in $HOME
# is redirected inside the project, so deleting the project directory leaves no
# trace on the system. Nothing here is exported into the user's shell profile.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PROJECT_DIR

TOOLS_DIR="$PROJECT_DIR/.tools"

# uv: never touch ~/.cache/uv, ~/.local/share/uv or a global uv config
export UV_CACHE_DIR="$TOOLS_DIR/cache/uv"
export UV_PYTHON_INSTALL_DIR="$TOOLS_DIR/python"
export UV_PYTHON_BIN_DIR="$TOOLS_DIR/bin"
export UV_TOOL_DIR="$TOOLS_DIR/uv-tools"
export UV_PYTHON_DOWNLOADS=never
export UV_NO_CONFIG=1
export UV_PROJECT_ENVIRONMENT="$PROJECT_DIR/.venv"

# Playwright: browsers live in the project, not ~/Library/Caches/ms-playwright
export PLAYWRIGHT_BROWSERS_PATH="$TOOLS_DIR/browsers"

# Generic XDG / temp redirection (Chromium scratch profiles, misc caches)
export XDG_CACHE_HOME="$TOOLS_DIR/cache"
export XDG_DATA_HOME="$TOOLS_DIR/share"
export XDG_CONFIG_HOME="$TOOLS_DIR/config"
export TMPDIR="$TOOLS_DIR/tmp"

mkdir -p "$UV_CACHE_DIR" "$PLAYWRIGHT_BROWSERS_PATH" "$TMPDIR"

VENV_PY="$PROJECT_DIR/.venv/bin/python"
