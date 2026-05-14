#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/LionelPinheiroDuarte/toolbox.git"

# Install pipx if missing
if ! command -v pipx &>/dev/null; then
    echo "pipx not found — installing..."
    if command -v apt &>/dev/null; then
        sudo apt install -y pipx
    else
        pip install --user pipx
    fi
    pipx ensurepath
    echo "Restart your shell or run: source ~/.bashrc"
fi

# Install toolbox
echo "Installing toolbox..."
pipx install "$REPO"

echo ""
echo "Done. The 'x' command is now available."
echo ""
echo "Required environment variables:"
echo "  OPENROUTER_API_KEY   — used by 'x wtf' for AI-powered error explanation"
echo ""
echo "Add to your shell config (~/.bashrc or ~/.bash_profile):"
echo "  export OPENROUTER_API_KEY=your_key_here"
