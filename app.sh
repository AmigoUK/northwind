#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python presence
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Run install.sh first."
    exit 1
fi

# Dependency check — if any import fails, run installer
if ! python3 -c "import textual, plotext, fpdf, PIL, qrcode, fastapi, uvicorn, barcode" 2>/dev/null; then
    echo "Some dependencies are missing. Running install.sh ..."
    bash "$SCRIPT_DIR/install.sh"
fi

python3 "$SCRIPT_DIR/app.py"
