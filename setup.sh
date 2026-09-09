#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python3.12 -m venv .venv
.venv/bin/python -m pip install --timeout 120 --retries 10 -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
.venv/bin/python backend/setup_ocr.py
echo 'Setup complete. Run bash start-backend.sh and bash start-frontend.sh in separate terminals.'
