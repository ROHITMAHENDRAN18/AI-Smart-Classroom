import json
import os
import threading
from datetime import datetime


class ClassroomAnalyticsManager:
    """
    STEP 12
    Persistent classroom-session analytics.

    Stores lightweight state snapshots in JSONL format so the project
    can calculate session summaries and student-wise attention metrics
    without changing the Step 9 detection pipeline.
    """

    def __init__(self, storage_dir=None, sample_seconds=5):
        base_dir = os.path.dirname(__file__)

        self.storage_dir = storage_dir or os.path.join(
            base_dir,
            "analytics_data"
        )

        self.history_file = os.path.join(
            self.storage_dir,
            "session_history.jsonl"
        )

        self.sample_seconds = max(1, int(sample_seconds))
        self._last_record_time = {}
        self._lock = threading.Lock()

        os.makedirs(self.storage_dir, exist_ok=True)

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalise_state(state):
        if not isinstance(state, dict):
            state = {}

        students = state.get("students", [])
        if not isinstance(students, list):
            students = []

        clean_students = []

        for student in students:
            if not isinstance(student, dict):
                continue

            clean_students.append({
                "track_id": student.get("track_id"),
                "student_id": student.get("student_id"),
                "recognized": bool(student.get("recognized", False)),
                "similarity": student.get("similarity"),
                "attention": str(
                    student.get("attention", "UNKNOWN")
                ).upper(),
                "yaw_ratio": student.get("yaw_ratio"),
                "pitch_ratio": student.get("pitch_ratio")
            })

        return {
            "timestamp": str(
                state.get(
                    "timestamp",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            ),
            "tracked_persons": int(
                state.get("tracked_persons", len(clean_students)) or 0
            ),
            "present_students": int(
                state.get(
                    "present_students",
                    sum(
                        1 for s in clean_students
                        if s.get("recognized")
                    )
                ) or 0
            ),
            "students": clean_students
        }

    @staticmethod
    def _student_key(student):
        student_id = student.get("student_id")

        if student_id:
            return str(student_id)

        track_id = student.get("track_id")

        if track_id is not None:
            return f"TRACK_{track_id}"

        return "UNKNOWN"

    # ---------------------------------------------------------
    # RECORD SNAPSHOT
    # ---------------------------------------------------------

    def record_state(self, session_id, state, force=False):
        """
        Save a sampled classroom snapshot.

        Returns True when a snapshot is written and False when
        sampling skipped the write.
        """

        if not session_id:
            return False

        now = datetime.now()
        now_epoch = now.timestamp()

        clean_state = self._normalise_state(state)

        with self._lock:

            last_time = self._last_record_time.get(session_id, 0)

            if (
                not force
                and now_epoch - last_time < self.sample_seconds
            ):
                return False

            record = {
                "session_id": str(session_id),
                "recorded_at": now.isoformat(timespec="seconds"),
                "state": clean_state
            }

            with open(
                self.history_file,
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False
                    ) + "\n"
                )

            self._last_record_time[session_id] = now_epoch

        return True

    # ---------------------------------------------------------
    # READ HISTORY
    # ---------------------------------------------------------

    def _read_records(self):
        records = []

        if not os.path.exists(self.history_file):
            return records

        try:
            with open(
                self.history_file,
                "r",
                encoding="utf-8"
            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:
                        continue

                    try:
                        item = json.loads(line)

                        if isinstance(item, dict):
                            records.append(item)

                    except json.JSONDecodeError:
                        continue

        except OSError:
            return []

        return records

    def get_session_records(self, session_id):
        return [
            item
            for item in self._read_records()
            if str(item.get("session_id")) == str(session_id)
        ]

    def list_sessions(self):
        sessions = {}

        for item in self._read_records():

            session_id = str(item.get("session_id", "UNKNOWN"))

            state = item.get("state", {})
            timestamp = state.get("timestamp")

            if session_id not in sessions:

                sessions[session_id] = {
                    "session_id": session_id,
                    "first_record": item.get("recorded_at"),
                    "last_record": item.get("recorded_at"),
                    "records": 0,
                    "last_state": state
                }

            session = sessions[session_id]

            session["last_record"] = item.get(
                "recorded_at",
                session["last_record"]
            )

            session["records"] += 1
            session["last_state"] = state

        result = list(sessions.values())

        result.sort(
            key=lambda item: item.get("last_record", ""),
            reverse=True
        )

        return result

    # ---------------------------------------------------------
    # SESSION SUMMARY
    # ---------------------------------------------------------

    def get_session_summary(self, session_id):
        records = self.get_session_records(session_id)

        if not records:
            return {
                "session_id": session_id,
                "records": 0,
                "duration_seconds": 0,
                "duration_minutes": 0,
                "peak_tracked_persons": 0,
                "peak_present_students": 0,
                "average_present_students": 0,
                "overall_attention_rate": 0,
                "overall_not_attention_rate": 0,
                "overall_unknown_rate": 0,
                "students": []
            }

        first_time = None
        last_time = None

        peak_tracked = 0
        peak_present = 0

        present_values = []

        attentive_samples = 0
        not_attentive_samples = 0
        unknown_samples = 0

        student_stats = {}

        for record in records:

            state = record.get("state", {})

            recorded_at = record.get("recorded_at")

            try:
                current_time = datetime.fromisoformat(
                    recorded_at
                )
            except (TypeError, ValueError):
                current_time = None

            if current_time:

                if first_time is None:
                    first_time = current_time

                last_time = current_time

            tracked = int(
                state.get("tracked_persons", 0) or 0
            )

            present = int(
                state.get("present_students", 0) or 0
            )

            peak_tracked = max(
                peak_tracked,
                tracked
            )

            peak_present = max(
                peak_present,
                present
            )

            present_values.append(present)

            students = state.get("students", [])

            if not isinstance(students, list):
                students = []

            for student in students:

                attention = str(
                    student.get(
                        "attention",
                        "UNKNOWN"
                    )
                ).upper()

                if attention == "ATTENTIVE":
                    attentive_samples += 1

                elif attention == "NOT ATTENTIVE":
                    not_attentive_samples += 1

                else:
                    unknown_samples += 1

                key = self._student_key(student)

                if key not in student_stats:

                    student_stats[key] = {
                        "student_id": (
                            student.get("student_id")
                            or key
                        ),
                        "samples": 0,
                        "attentive": 0,
                        "not_attentive": 0,
                        "unknown": 0,
                        "attention_rate": 0
                    }

                stats = student_stats[key]

                stats["samples"] += 1

                if attention == "ATTENTIVE":
                    stats["attentive"] += 1

                elif attention == "NOT ATTENTIVE":
                    stats["not_attentive"] += 1

                else:
                    stats["unknown"] += 1

        duration_seconds = 0

        if first_time and last_time:

            duration_seconds = max(
                0,
                int(
                    (last_time - first_time).total_seconds()
                )
            )

        total_attention_samples = (
            attentive_samples
            + not_attentive_samples
            + unknown_samples
        )

        if total_attention_samples > 0:

            overall_attention_rate = round(
                attentive_samples
                / total_attention_samples
                * 100,
                1
            )

            overall_not_attention_rate = round(
                not_attentive_samples
                / total_attention_samples
                * 100,
                1
            )

            overall_unknown_rate = round(
                unknown_samples
                / total_attention_samples
                * 100,
                1
            )

        else:

            overall_attention_rate = 0
            overall_not_attention_rate = 0
            overall_unknown_rate = 0

        students_result = []

        for stats in student_stats.values():

            samples = stats["samples"]

            if samples > 0:
                stats["attention_rate"] = round(
                    stats["attentive"]
                    / samples
                    * 100,
                    1
                )

            students_result.append(stats)

        students_result.sort(
            key=lambda item: str(item["student_id"])
        )

        average_present = 0

        if present_values:
            average_present = round(
                sum(present_values)
                / len(present_values),
                1
            )

        return {
            "session_id": session_id,
            "records": len(records),
            "started_at": (
                first_time.isoformat(timespec="seconds")
                if first_time else None
            ),
            "last_record_at": (
                last_time.isoformat(timespec="seconds")
                if last_time else None
            ),
            "duration_seconds": duration_seconds,
            "duration_minutes": round(
                duration_seconds / 60,
                1
            ),
            "peak_tracked_persons": peak_tracked,
            "peak_present_students": peak_present,
            "average_present_students": average_present,
            "overall_attention_rate": overall_attention_rate,
            "overall_not_attention_rate": overall_not_attention_rate,
            "overall_unknown_rate": overall_unknown_rate,
            "students": students_result
        }

    # ---------------------------------------------------------
    # TIMELINE
    # ---------------------------------------------------------

    def get_timeline(self, session_id, limit=300):
        records = self.get_session_records(session_id)

        result = []

        for record in records[-limit:]:

            state = record.get("state", {})

            attentive = 0
            not_attentive = 0
            unknown = 0

            students = state.get("students", [])

            if isinstance(students, list):

                for student in students:

                    attention = str(
                        student.get(
                            "attention",
                            "UNKNOWN"
                        )
                    ).upper()

                    if attention == "ATTENTIVE":
                        attentive += 1

                    elif attention == "NOT ATTENTIVE":
                        not_attentive += 1

                    else:
                        unknown += 1

            result.append({
                "recorded_at": record.get("recorded_at"),
                "timestamp": state.get("timestamp"),
                "tracked_persons": state.get(
                    "tracked_persons",
                    0
                ),
                "present_students": state.get(
                    "present_students",
                    0
                ),
                "attentive": attentive,
                "not_attentive": not_attentive,
                "unknown": unknown
            })

        return result
