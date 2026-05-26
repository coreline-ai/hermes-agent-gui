#!/usr/bin/env bash
# hermes-agent-gui — daemon lifecycle wrapper (Phase 10).
#
# Adapted from nesquena/hermes-webui's ctl.sh. No fuser / pkill required —
# we track a single PID file under ~/.hermes-agent-gui/.
#
# Usage:
#   ./scripts/ctl.sh start              # background daemon
#   ./scripts/ctl.sh status             # PID, uptime, host/port, log path
#   ./scripts/ctl.sh logs [--lines N]   # tail
#   ./scripts/ctl.sh restart
#   ./scripts/ctl.sh stop
#
# Env: HERMES_GUI_HOST, HERMES_GUI_PORT, HERMES_GUI_PASSWORD, ...

set -euo pipefail

STATE_DIR="${HERMES_GUI_STATE_DIR:-$HOME/.hermes-agent-gui}"
PID_FILE="$STATE_DIR/gui.pid"
LOG_FILE="$STATE_DIR/gui.log"
HOST="${HERMES_GUI_HOST:-127.0.0.1}"
PORT="${HERMES_GUI_PORT:-8800}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$ROOT_DIR/apps/server/server.py"

mkdir -p "$STATE_DIR"

case "${1:-help}" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "already running: pid $(cat "$PID_FILE")"
      exit 0
    fi
    echo "starting on $HOST:$PORT (log: $LOG_FILE)"
    nohup python3 "$SERVER_PY" --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 0.5
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "started: pid $(cat "$PID_FILE")"
    else
      echo "failed to start — check $LOG_FILE"; exit 1
    fi
    ;;

  stop)
    if [ ! -f "$PID_FILE" ]; then echo "not running"; exit 0; fi
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"; sleep 0.5
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" || true
      echo "stopped: pid $pid"
    fi
    rm -f "$PID_FILE"
    ;;

  restart)
    "$0" stop || true
    "$0" start
    ;;

  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      pid=$(cat "$PID_FILE")
      echo "running: pid $pid"
      echo "host:    $HOST"
      echo "port:    $PORT"
      echo "log:     $LOG_FILE"
      curl -fsS "http://$HOST:$PORT/api/health" 2>/dev/null || echo "(health probe failed)"
    else
      echo "not running"; exit 1
    fi
    ;;

  logs)
    lines=100
    while [ $# -gt 1 ]; do
      case "$2" in
        --lines) lines="$3"; shift 2;;
        *) shift;;
      esac
    done
    tail -n "$lines" -F "$LOG_FILE"
    ;;

  *)
    cat <<EOF
usage: ctl.sh <command>
  start     run in background
  stop      send SIGTERM (then SIGKILL after 0.5s)
  restart   stop + start
  status    pid, host:port, /api/health probe
  logs      tail [--lines N]
EOF
    exit 64
    ;;
esac
