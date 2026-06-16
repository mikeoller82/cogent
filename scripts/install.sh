#!/usr/bin/env bash
# Cogent install script
set -euo pipefail

COGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing Cogent..."

# Run setup
bash "$COGENT_DIR/scripts/setup.sh"

# Create .env if missing
if [ ! -f "$COGENT_DIR/backend/.env" ]; then
    cat > "$COGENT_DIR/backend/.env" << 'EOF'
# Cogent Configuration
# Copy and fill in your API keys
KILOCODE_API_KEY=
EOF
    echo "Created .env template. Edit backend/.env to add your API key."
fi

echo ""
echo "Cogent installed!"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your KILOCODE_API_KEY"
echo "  2. Start the server: python backend/server.py"
echo "  3. Or use CLI: python -m backend.cli server start"
