#!/usr/bin/env bash
# Restart APAFIX application (graceful reload)
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="/var/run/apafix/apafix.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    PID=$(cat "$PIDFILE")
    echo "Reloading APAFIX (PID $PID)..."
    # SIGHUP = graceful reload (new workers, old ones finish their requests)
    kill -HUP "$PID"
    echo "APAFIX reloaded"
else
    echo "APAFIX is not running, starting..."
    "$APP_DIR/start.sh"
fi
