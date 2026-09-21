#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

source "$PROJECT_ROOT/.venv/bin/activate"

echo "============================================================"
echo "AI SMART CLASSROOM SYSTEM"
echo "============================================================"
echo ""
echo "Starting Dashboard..."
echo ""

python -m dashboard.classroom_dashboard &
DASHBOARD_PID=$!

sleep 2

cleanup() {
    echo ""
    echo "============================================================"
    echo "Stopping AI Smart Classroom..."
    echo "============================================================"

    if kill -0 "$DASHBOARD_PID" 2>/dev/null; then
        echo "Stopping Dashboard..."
        kill "$DASHBOARD_PID" 2>/dev/null
        wait "$DASHBOARD_PID" 2>/dev/null
    fi

    echo "Dashboard stopped."
    echo "System stopped."
    echo "============================================================"
}

trap cleanup INT TERM EXIT

echo ""
echo "Starting AI Pipeline..."
echo ""

python -m ai.face_recognition.face_track_association

AI_STATUS=$?

exit "$AI_STATUS"