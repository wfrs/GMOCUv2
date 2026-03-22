#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/frontend"

if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies with npm ci..."
  npm ci
fi

exec npm run dev
