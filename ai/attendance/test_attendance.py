import csv
from datetime import datetime, timedelta

from ai.attendance.attendance_manager import AttendanceManager


def _manager_for_path(path):
    manager = AttendanceManager()
    manager.attendance_file = str(path)
    return manager


def test_today_count_is_read_only_and_counts_distinct_present_students(tmp_path):
    path = tmp_path / "attendance.csv"
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    rows = [
        ["student_id", "track_id", "similarity", "date", "time", "status"],
        ["S1", "1", "0.9", today, "09:00:00", "Present"],
        ["S1", "2", "0.8", today, "10:00:00", "PRESENT"],
        ["S2", "3", "0.9", yesterday, "09:00:00", "Present"],
        ["S3", "4", "0.9", today, "11:00:00", "Absent"],
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows(rows)
    original = path.read_bytes()

    manager = _manager_for_path(path)

    assert manager.get_today_count() == 1
    assert path.read_bytes() == original


def test_today_count_returns_zero_when_file_is_missing(tmp_path):
    manager = _manager_for_path(tmp_path / "missing.csv")

    assert manager.get_today_count() == 0


def test_mark_present_updates_today_count_once(tmp_path):
    manager = _manager_for_path(tmp_path / "attendance.csv")

    assert manager.mark_present("S1", track_id=7, similarity=0.91) is True
    assert manager.mark_present("S1", track_id=7, similarity=0.91) is False
    assert manager.get_today_count() == 1
    assert manager.get_present_count() == 1