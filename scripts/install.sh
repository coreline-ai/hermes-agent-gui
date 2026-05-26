#!/usr/bin/env bash
# hermes-agent-gui — one-line installer (Phase 10).
# Inspired by outsourc-e/hermes-workspace's install.sh.

set -euo pipefail

ROOT="$HOME/hermes-agent-gui"
REPO_URL="${HERMES_GUI_REPO:-https://github.com/your-org/hermes-agent-gui.git}"

echo "→ hermes-agent-gui installer"

if [ -d "$ROOT" ]; then
  echo "[ok] $ROOT already exists — pulling latest"
  (cd "$ROOT" && git pull --ff-only || true)
else
  echo "[1/4] clone → $ROOT"
  git clone "$REPO_URL" "$ROOT"
fi

cd "$ROOT"

echo "[2/4] python deps"
python3 -m pip install -r apps/server/requirements.txt

echo "[3/4] node deps (pnpm)"
if ! command -v pnpm >/dev/null 2>&1; then
  echo "  installing pnpm via corepack"
  corepack enable && corepack prepare pnpm@latest --activate
fi
pnpm install

echo "[4/4] done"
cat <<EOF

Next:
  cd $ROOT
  HERMES_GUI_PASSWORD=changeme \\
  HERMES_GUI_FAKE_BACKEND=echo \\
    ./scripts/ctl.sh start

  pnpm dev   # http://localhost:5173

For zero-fork mode against an existing Hermes Agent:
  HERMES_GUI_PASSWORD=... HERMES_API_URL=http://127.0.0.1:8642 ./scripts/ctl.sh start

EOF
