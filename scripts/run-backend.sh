#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing repo virtualenv at $ROOT_DIR/.venv"
  echo "Create it first, then rerun this script."
  exit 1
fi

cd "$ROOT_DIR/backend"

exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --reload
