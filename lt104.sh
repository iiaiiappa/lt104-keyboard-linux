#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/web_app.py" 8989 &
PID=$!
sleep 0.5
xdg-open "http://127.0.0.1:8989" 2>/dev/null || sensible-browser "http://127.0.0.1:8989" 2>/dev/null
wait $PID
