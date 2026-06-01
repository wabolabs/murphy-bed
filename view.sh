#!/usr/bin/env bash
set -e
PORT=${1:-8080}
echo "→ Starting server on http://localhost:$PORT"
python3 -m http.server "$PORT" &
PID=$!
sleep 1
URL="http://localhost:$PORT/design/3d/viewer.html"
echo "→ Opening $URL"
case "$(uname -s)" in
  Linux*)  xdg-open "$URL" ;;
  Darwin*) open "$URL" ;;
  CYGWIN*|MINGW*|MSYS*) powershell.exe Start-Process "$URL" ;;
esac
wait $PID 2>/dev/null || true