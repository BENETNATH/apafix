#!/usr/bin/env bash
# Start APAFIX application
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${APP_DIR}/venv"
PID_DIR="/var/run/apafix"
LOG_DIR="/var/log/apafix"

# Ensure directories exist
sudo mkdir -p "$PID_DIR" "$LOG_DIR"
sudo chown "$(whoami)" "$PID_DIR" "$LOG_DIR"

# Activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Run: python3 -m venv $VENV_DIR && $VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt"
    exit 1
fi
source "$VENV_DIR/bin/activate"

cd "$APP_DIR"

# Check if already running
PIDFILE="$PID_DIR/apafix.pid"
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "APAFIX is already running (PID $PID)"
        exit 1
    else
        echo "Stale PID file found, removing..."
        rm -f "$PIDFILE"
    fi
fi

# Initialize database and create admin if needed
python -c "from app import app; print('App initialized')"
flask create-admin 2>/dev/null || true

# Start gunicorn
echo "Starting APAFIX..."
gunicorn \
    --config "$APP_DIR/gunicorn.conf.py" \
    --daemon \
    wsgi:app

sleep 1
if [ -f "$PIDFILE" ]; then
    echo "APAFIX started (PID $(cat "$PIDFILE"))"
    echo "Listening on $(grep -oP 'bind\s*=.*"(.+)"' "$APP_DIR/gunicorn.conf.py" | head -1 || echo '0.0.0.0:8000')"
else
    echo "APAFIX started"
fi
