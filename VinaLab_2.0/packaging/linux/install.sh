#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[ui]"

cat <<'EOF'

VinaLab 2.0 is installed in .venv.
Before docking, install Linux AutoDock Vina and xTB binaries, then run:
  source .venv/bin/activate
  vinalab
EOF
