#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Northwind Traders — Installer ==="

# Python presence
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ from https://www.python.org"
    exit 1
fi

# Python version >= 3.9
python3 - <<'EOF'
import sys
if sys.version_info < (3, 9):
    print(f"ERROR: Python 3.9+ required, found {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)
EOF

echo "Python $(python3 --version) OK"

# Install packages
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Installation complete. Run:  bash app.sh"
