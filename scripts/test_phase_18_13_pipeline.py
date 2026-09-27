"""Read-only Phase 18.13 integration checks.

This script verifies config, PostgreSQL schema/connectivity, persisted state,
and the existing backend/dashboard HTTP APIs. It never starts the AI pipeline,
camera, or model inference and performs no writes.
"""

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import inspect, text

from backend.database.connection import engine
from configs.settings import (
    API_VERSION,
    DASHBOARD_HOST,
    DASHBOARD_PORT,
    DATABASE_URL,
    HOST,
    PORT,
    PROJECT_NAME,
    PROJECT_VERSION,
    YOLO_MODEL,
)


STATE_FILE = Path("dashboard/classroom_state.json")
REQUIRED_TABLES = {
    "students",
    "classroom_sessions",
    "attendance_records",
    "attention_records",
}
REQUIRED_ATTENTION_COLUMNS = {
    "track_id",
    "attention_state",
    "attention_score",
    "fusion_state",
    "fusion_score",
    "fusion_confidence",
    "temporal_state",
    "temporal_score",
    "temporal_confidence",
    "temporal_stable",
    "recorded_at",
}


def _get_json(url):
    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"{url} returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def check_configuration():
    assert PROJECT_NAME and PROJECT_VERSION and YOLO_MODEL
    assert DATABASE_URL and HOST and PORT > 0
    assert DASHBOARD_HOST and DASHBOARD_PORT > 0
    print("[PASS] Configuration")


def check_database():
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        assert not REQUIRED_TABLES - tables, REQUIRED_TABLES - tables

        columns = {
            column["name"]
            for column in inspector.get_columns("attention_records")
        }
        assert not REQUIRED_ATTENTION_COLUMNS - columns, (
            REQUIRED_ATTENTION_COLUMNS - columns
        )
    print("[PASS] PostgreSQL connectivity, tables, and attention schema")


def check_classroom_state():
    if not STATE_FILE.exists():
        print("[WARN] classroom_state.json does not exist yet")
        return

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    assert isinstance(state, dict)
    assert isinstance(state.get("students", []), list)
    for student in state.get("students", []):
        assert isinstance(student, dict)
        assert "attention" in student
        assert student.get("fusion") is None or isinstance(student["fusion"], dict)
        assert student.get("temporal") is None or isinstance(student["temporal"], dict)
    print("[PASS] Classroom state JSON and optional fusion/temporal payloads")


def check_backend_api():
    base_url = f"http://{HOST}:{PORT}"
    assert _get_json(f"{base_url}/").get("status") == "Backend Running"
    assert _get_json(f"{base_url}{API_VERSION.rstrip('/')}/health").get("status") == "Healthy"
    assert _get_json(f"{base_url}{API_VERSION.rstrip('/')}/database").get("success") is True
    print("[PASS] Backend root, health, and database APIs")


def check_dashboard_api():
    base_url = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"
    assert _get_json(f"{base_url}/health").get("status") == "ok"

    state = _get_json(f"{base_url}/api/state")
    assert isinstance(state.get("students"), list)
    for student in state.get("students", []):
        assert "attention" in student
        assert student.get("fusion") is None or isinstance(student["fusion"], dict)
        assert student.get("temporal") is None or isinstance(student["temporal"], dict)

    alerts = _get_json(f"{base_url}/api/alerts")
    assert "alerts" in alerts and "statistics" in alerts

    sessions = _get_json(f"{base_url}/api/sessions")
    assert isinstance(sessions, list)
    if sessions:
        session_id = sessions[0].get("session_id")
        query = urlencode({"session_id": session_id})
        assert _get_json(f"{base_url}/api/session?{query}")
        assert _get_json(f"{base_url}/api/analytics?{query}")

    print("[PASS] Dashboard health, state, alerts, sessions, and analytics APIs")


def main():
    print("PHASE 18.13 READ-ONLY PIPELINE INTEGRATION CHECK")
    print("=" * 55)
    checks = (
        check_configuration,
        check_database,
        check_classroom_state,
        check_backend_api,
        check_dashboard_api,
    )
    for check in checks:
        check()
    print("=" * 55)
    print(f"RESULT: {len(checks)}/{len(checks)} checks passed")


if __name__ == "__main__":
    main()
