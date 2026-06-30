#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/LionelPinheiroDuarte/toolbox.git"
MIN_PYTHON_MINOR=8

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}$*${RESET}"; }

# ── Python ────────────────────────────────────────────────────────────────────
info "\n[1/3] Checking Python..."

if ! command -v python3 &>/dev/null; then
    fail "Python 3 not found. Install it from https://www.python.org/downloads/"
fi

PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")

if [[ "$PYTHON_MAJOR" -lt 3 || "$PYTHON_MINOR" -lt "$MIN_PYTHON_MINOR" ]]; then
    fail "Python 3.${MIN_PYTHON_MINOR}+ required (found $(python3 --version))"
fi

ok "Python $(python3 --version | cut -d' ' -f2)"

# ── pipx ──────────────────────────────────────────────────────────────────────
info "\n[2/3] Checking pipx..."

if ! command -v pipx &>/dev/null; then
    warn "pipx not found — installing..."
    if command -v apt &>/dev/null; then
        sudo apt install -y pipx
    else
        python3 -m pip install --user pipx
    fi
    pipx ensurepath
    export PATH="$PATH:$HOME/.local/bin"
fi

ok "pipx $(pipx --version)"

# ── toolbox ───────────────────────────────────────────────────────────────────
info "\n[3/3] Installing toolbox..."

if pipx list 2>/dev/null | grep -q "toolbox"; then
    warn "toolbox already installed — reinstalling..."
    pipx uninstall toolbox
fi

pipx install "git+$REPO"
ok "toolbox installed"

# ── Optional dependencies ─────────────────────────────────────────────────────
echo ""
info "Optional dependencies:"

if command -v batcat &>/dev/null || command -v bat &>/dev/null; then
    ok "batcat — x notes will work"
else
    warn "batcat not found — x notes requires it (sudo apt install bat)"
fi

if command -v gh &>/dev/null; then
    ok "gh CLI — x repos will work"
else
    warn "gh CLI not found — x repos requires it (https://cli.github.com)"
fi

# ── Post-install ──────────────────────────────────────────────────────────────
echo ""
info "Setup required:"
echo ""
echo "  x wtf    → set OPENROUTER_API_KEY in your shell config:"
echo "             export OPENROUTER_API_KEY=your_key_here"
echo ""
echo "  x sync   → run once to configure Nextcloud credentials:"
echo "             x sync --configure"
echo ""
ok "Done. Run 'x --help' to get started."
echo ""
