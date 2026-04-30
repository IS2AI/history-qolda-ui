#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/frontend"

source /shared/home/galammadin.askar/miniconda3/bin/activate qolda_stack

# Load .env from project root
export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs) 2>/dev/null || true

exec python app.py
