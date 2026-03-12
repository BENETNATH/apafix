#!/usr/bin/env bash
# Stop APAFIX application
set -euo pipefail

PIDFILE="/var/run/apafix/apafix.pid"

if [ ! -f "$PIDFILE" ]; then
    echo "APAFIX is not running (no PID file)"
    exit 0
fi

PID=$(cat "$PIDFILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "APAFIX is not running (stale PID $PID), cleaning up..."
    rm -f "$PIDFILE"
    exit 0
fi

echo "Stopping APAFIX (PID $PID)..."
kill -TERM "$PID"

# Wait for graceful shutdown (max 10s)
for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "APAFIX stopped"
        rm -f "$PIDFILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "Force killing APAFIX..."
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PIDFILE"
echo "APAFIX stopped (forced)"
