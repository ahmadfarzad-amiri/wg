#!/usr/bin/env bash
# Pack client-panel + admin-panel for production deployment.
# Usage: bash client-panel/deploy/export-bundle.sh [output.tar.gz]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$REPO_ROOT/wg-production.tar.gz}"
STAGE="$(mktemp -d)"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

mkdir -p "$STAGE/wg"

rsync -a \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='local-data' \
  --exclude='*.bak.*' \
  "$REPO_ROOT/client-panel/" "$STAGE/wg/client-panel/"

rsync -a \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='local-data' \
  --exclude='*.bak.*' \
  "$REPO_ROOT/admin-panel/" "$STAGE/wg/admin-panel/"

tar -czf "$OUT" -C "$STAGE" wg

echo "Created: $OUT"
echo ""
echo "On the server:"
echo "  sudo mkdir -p /opt/wg"
echo "  sudo tar -xzf wg-production.tar.gz -C /opt/wg --strip-components=1"
echo "  sudo systemctl restart wg-panel wg-admin-panel"
