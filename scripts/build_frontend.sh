#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$REPO_ROOT/frontend"

cd "$FRONTEND"

# Install deps if node_modules missing or stale
if [ ! -d node_modules ] || [ package.json -nt node_modules ]; then
  echo "Installing dependencies..."
  yarn install --frozen-lockfile 2>/dev/null || yarn install
fi

echo "Building frontend packages..."
yarn build
