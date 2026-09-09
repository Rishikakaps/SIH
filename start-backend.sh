#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/backend"
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
