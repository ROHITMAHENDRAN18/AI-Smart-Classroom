#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

source "$PROJECT_ROOT/.venv/bin/activate"

DASHBOARD_PID=""
CLEANUP_DONE=0

echo "============================================================"
echo "AI SMART CLASSROOM SYSTEM"
echo "============================================================"
echo ""
echo "Starting Dashboard..."
echo ""

python -m dashboard.classroom_dashboard &
DASHBOARD_PID=$!

cleanup() {
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi

    CLEANUP_DONE=1

    echo ""
    echo "============================================================"
    echo "Stopping AI Smart Classroom..."
    echo "============================================================"

    if [ -n "$DASHBOARD_PID" ] && kill -0 "$DASHBOARD_PID" 2>/dev/null; then
        echo "Stopping Dashboard..."
        kill "$DASHBOARD_PID" 2>/dev/null
        wait "$DASHBOARD_PID" 2>/dev/null
    fi

    echo "Dashboard stopped."
    echo "System stopped."
    echo "============================================================"
}

trap cleanup INT TERM EXIT

echo "Waiting for Dashboard..."
echo ""

DASHBOARD_READY=0

for i in {1..15}; do
    if curl -s --max-time 1 http://127.0.0.1:5050/health > /tmp/ai_smart_classroom_health.json 2>/dev/null; then
        DASHBOARD_READY=1
        break
    fi

    sleep 1
done

if [ "$DASHBOARD_READY" -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "DASHBOARD HEALTH CHECK FAILED"
    echo "============================================================"
    echo ""
    echo "Dashboard did not become ready on port 5050."
    echo "AI Pipeline will NOT be started."
    echo ""
    exit 1
fi

echo "============================================================"
echo "SYSTEM HEALTH CHECK"
echo "============================================================"
echo ""
echo "Dashboard : ONLINE"
echo "Port      : 5050"
echo "Health    : OK"
echo ""
echo "Starting AI Pipeline..."
echo ""

python -m ai.face_recognition.face_track_association

AI_STATUS=$?

exit "$AI_STATUS"