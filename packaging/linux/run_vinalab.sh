#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -x "$SCRIPT_DIR/VinaLab" ]; then
  APP_ROOT="$SCRIPT_DIR"
  export QTWEBENGINE_DISABLE_SANDBOX="${QTWEBENGINE_DISABLE_SANDBOX:-1}"
  if [ -z "${QTWEBENGINE_CHROMIUM_FLAGS:-}" ]; then
    export QTWEBENGINE_CHROMIUM_FLAGS="--single-process --no-sandbox --disable-gpu"
  fi
  export PATH="$APP_ROOT/tools/gnina:$APP_ROOT/tools/vina:$APP_ROOT/openbabel/bin:$APP_ROOT/openbabel:${PATH:-}"
  export LD_LIBRARY_PATH="$APP_ROOT:$APP_ROOT/tools/gnina:$APP_ROOT/tools/vina:$APP_ROOT/openbabel/lib:$APP_ROOT/openbabel/bin:$APP_ROOT/openbabel:${LD_LIBRARY_PATH:-}"
  cd "$APP_ROOT"
  exec "$APP_ROOT/VinaLab" "$@"
fi

PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python launcher.py
