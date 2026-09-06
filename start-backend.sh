#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
PYTHON_BIN="/Users/rishika/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
VENV="/private/tmp/rx-lens-backend-venv"
RUNTIME_SRC="/private/tmp/rx-lens-backend-src"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating backend runtime venv at $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi

if "$VENV/bin/python" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Backend dependencies already available."
else
  echo "Installing backend dependencies. First run can take a few minutes because EasyOCR installs ML packages..."
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt"
fi

echo "Copying backend source to fast local runtime path..."
mkdir -p "$RUNTIME_SRC"
rm -rf "$RUNTIME_SRC/app" "$RUNTIME_SRC/tests"
cp -R "$BACKEND/app" "$RUNTIME_SRC/app"
cp -R "$BACKEND/tests" "$RUNTIME_SRC/tests"

echo "Starting Rx Lens backend at http://127.0.0.1:8000"
cd "$RUNTIME_SRC"
PYTHONPATH=. "$VENV/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
