#!/usr/bin/env bash
# Run Cogent test suite
set -euo pipefail

COGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

source "$COGENT_DIR/backend/.venv/bin/activate"
cd "$COGENT_DIR"

python -m pytest tests/ -v "$@"
