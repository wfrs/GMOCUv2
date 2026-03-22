#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_URL="http://127.0.0.1:8000/api/health"

is_expected_dev_process() {
  local command="$1"
  [[ "$command" == *uvicorn* || "$command" == *vite* || "$command" == *npm* || "$command" == *node* || "$command" == *python* ]]
}

stop_port_if_needed() {
  local port="$1"
  local pids
  local pid
  local command

  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  [[ -z "$pids" ]] && return

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ -z "$command" ]]; then
      continue
    fi
    if ! is_expected_dev_process "$command"; then
      echo "Port $port is already in use by an unexpected process:"
      echo "  PID $pid: $command"
      echo "Refusing to kill it automatically."
      exit 1
    fi
    echo "Stopping existing dev process on port $port:"
    echo "  PID $pid: $command"
    kill "$pid" 2>/dev/null || true
  done <<< "$pids"

  for _ in {1..20}; do
    if ! lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return
    fi
    sleep 0.25
  done

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  [[ -z "$pids" ]] && return

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    echo "Force-stopping stubborn dev process on port $port (PID $pid)"
    kill -9 "$pid" 2>/dev/null || true
  done <<< "$pids"
}

wait_for_backend() {
  local attempts=60

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$BACKEND_URL" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Backend exited before becoming ready."
      return 1
    fi
    sleep 0.5
  done

  echo "Backend did not become ready at $BACKEND_URL in time."
  return 1
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

stop_port_if_needed 8000
stop_port_if_needed 5173

"$ROOT_DIR/scripts/run-backend.sh" &
BACKEND_PID=$!

echo "Starting backend on http://localhost:8000"
wait_for_backend
echo "Backend is ready"

echo "Starting frontend on http://localhost:5173"
"$ROOT_DIR/scripts/run-frontend.sh" &
FRONTEND_PID=$!

wait "$FRONTEND_PID"
