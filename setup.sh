#!/bin/sh
# One-time bootstrap. Everything it creates lives inside this project directory:
#   .venv/          python virtual environment
#   .tools/         playwright's chromium, caches, temp
#   templates/fonts embedded fonts
# Deleting the project directory removes all of it.
set -eu

. "$(cd "$(dirname "$0")" && pwd)/env.sh"

say() { printf '\033[1m==>\033[0m %s\n' "$1"; }
die() { printf '\033[31mError:\033[0m %s\n' "$1" >&2; exit 1; }

command -v uv >/dev/null 2>&1 || die "uv is required but not on PATH (see https://docs.astral.sh/uv/)."
command -v curl >/dev/null 2>&1 || die "curl is required but not on PATH."

say "Creating virtual environment (.venv) with system Python 3.14"
uv venv --python 3.14 --python-preference only-system "$PROJECT_DIR/.venv"

say "Installing python dependencies"
uv pip install --python "$VENV_PY" -r "$PROJECT_DIR/requirements.txt"

say "Installing headless Chromium into .tools/browsers"
"$VENV_PY" -m playwright install --only-shell chromium

say "Downloading fonts into templates/fonts"
FONT_DIR="$PROJECT_DIR/templates/fonts"
mkdir -p "$FONT_DIR"
GF="https://raw.githubusercontent.com/google/fonts/main/ofl"
fetch() {
    # fetch <url> <destination>
    [ -s "$2" ] && { printf '    %s (already present)\n' "$(basename "$2")"; return 0; }
    curl -fsSL --retry 3 -o "$2.part" "$1" || die "download failed: $1"
    mv "$2.part" "$2"
    printf '    %s\n' "$(basename "$2")"
}
fetch "$GF/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf" "$FONT_DIR/JetBrainsMono-variable.ttf"
fetch "$GF/jetbrainsmono/OFL.txt"                     "$FONT_DIR/JetBrainsMono-OFL.txt"
fetch "$GF/inter/Inter%5Bopsz%2Cwght%5D.ttf"          "$FONT_DIR/Inter-variable.ttf"
fetch "$GF/inter/OFL.txt"                             "$FONT_DIR/Inter-OFL.txt"

say "Done. Try:"
printf '    ./qrpages single --ssid "My Network" --password "s3cret-pass" --comment "Living room"\n'
printf '    ./qrpages bulk\n'
