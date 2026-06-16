#!/usr/bin/env bash
# Cogent setup script — mirrors Hermes' install scripts
set -euo pipefail

COGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Check Python
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 required"; exit 1; }

# Create virtual environment if missing
if [ ! -d "$COGENT_DIR/backend/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$COGENT_DIR/backend/.venv"
fi

# Install dependencies
source "$COGENT_DIR/backend/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$COGENT_DIR/backend/requirements.txt"

# Create required directories
mkdir -p "$COGENT_DIR/memory/sessions"
mkdir -p "$COGENT_DIR/memory/loops"
mkdir -p "$COGENT_DIR/memory/memories"
mkdir -p "$COGENT_DIR/memory/cron/output"
mkdir -p "$COGENT_DIR/memory/cache"
mkdir -p "$COGENT_DIR/memory/snapshots"
mkdir -p "$COGENT_DIR/backend/artifacts"
mkdir -p "$COGENT_DIR/backend/uploads"
mkdir -p "$COGENT_DIR/backend/logs"
mkdir -p "$COGENT_DIR/backend/hooks"
mkdir -p "$COGENT_DIR/sandboxes"
mkdir -p "$COGENT_DIR/.cogent/skills"

# Init seed files if missing
for f in kanban.json auth.json processes.json; do
    target="$COGENT_DIR/memory/$f"
    if [ ! -f "$target" ]; then
        echo "{}" > "$target"
        echo "Created $target"
    fi
done

if [ ! -f "$COGENT_DIR/memory/cron/jobs.json" ]; then
    echo "{\"jobs\": {}}" > "$COGENT_DIR/memory/cron/jobs.json"
fi

if [ ! -f "$COGENT_DIR/memory/memories/MEMORY.md" ]; then
    cat > "$COGENT_DIR/memory/memories/MEMORY.md" << 'EOF'
# Cogent Agent Memory

Facts, learnings, and context that survive across sessions.

EOF
fi

echo "Cogent setup complete."
