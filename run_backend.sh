#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

source /shared/home/galammadin.askar/miniconda3/bin/activate qolda_stack

# Load .env from project root
export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs) 2>/dev/null || true

exec uvicorn app.main:app \
    --host "${BACKEND_HOST:-0.0.0.0}" \
    --port "${BACKEND_PORT:-8035}" \
    --log-level "$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')" \
    --no-access-log
