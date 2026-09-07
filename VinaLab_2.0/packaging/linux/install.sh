#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e "$PROJECT_ROOT"
.venv/bin/python "$PROJECT_ROOT/packaging/build_support.py"

cat <<'EOF'

VinaLab 2.0 is installed in .venv.
Before docking, install Linux AutoDock Vina and xTB binaries, then run:
  source .venv/bin/activate
  vinalab
EOF
