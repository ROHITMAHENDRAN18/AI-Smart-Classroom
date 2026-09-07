import json
import os
from datetime import datetime


class ClassroomSessionManager:
    """
    Manages one classroom monitoring session.

    Responsibilities:
    - Start a classroom session
    - Record classroom state snapshots
    - Track students observed during the session
    - Stop the session
    - Save the complete session as JSON
    """

    def __init__(self, sessions_dir=None):

        if sessions_dir is None:

            sessions_dir = os.path.join(
                os.path.dirname(__file__),
                "sessions"
            )

        self.sessions_dir = sessions_dir

        os.makedirs(
            self.sessions_dir,
            exist_ok=True
        )

        self.active = False

        self.session_id = None

        self.started_at = None

        self.ended_at = None

        self.snapshots = []

        self.students_seen = {}

    # ========================================================
    # START SESSION
    # ========================================================

    def start_session(self):

        if self.active:

            return self.session_id

        now = datetime.now()

        self.session_id = (
            "SESSION_"
            + now.strftime("%Y%m%d_%H%M%S")
        )

        self.started_at = (
            now.isoformat(
                timespec="seconds"
            )
        )

        self.ended_at = None

        self.snapshots = []

        self.students_seen = {}

        self.active = True

        print()
        print("=" * 60)
        print("CLASSROOM SESSION STARTED")
        print("=" * 60)
        print(f"Session ID : {self.session_id}")
        print(f"Started    : {self.started_at}")
        print("=" * 60)
        print()

        return self.session_id

    # ========================================================
    # RECORD CLASSROOM STATE
    # ========================================================

    def record_state(self, state):

        if not self.active:

            return

        if not isinstance(state, dict):

            return

        now = datetime.now()

        snapshot = {

            "timestamp": now.isoformat(
                timespec="seconds"
            ),

            "tracked_persons":
                state.get(
                    "tracked_persons",
                    0
                ),

            "present_students":
                state.get(
                    "present_students",
                    0
                ),

            "students":
                state.get(
                    "students",
                    []
                )
        }

        self.snapshots.append(
            snapshot
        )

        students = snapshot["students"]

        if isinstance(
            students,
            list
        ):

            for student in students:

                if not isinstance(
                    student,
                    dict
                ):

                    continue

                student_id = (
                    student.get(
                        "student_id"
                    )
                    or "UNKNOWN"
                )

                if student_id == "UNKNOWN":

                    continue

                if student_id not in self.students_seen:

                    self.students_seen[
                        student_id
                    ] = {

                        "student_id":
                            student_id,

                        "first_seen":
                            snapshot[
                                "timestamp"
                            ],

                        "last_seen":
                            snapshot[
                                "timestamp"
                            ],

                        "observations":
                            0
                    }

                self.students_seen[
                    student_id
                ][
                    "last_seen"
                ] = snapshot[
                    "timestamp"
                ]

                self.students_seen[
                    student_id
                ][
                    "observations"
                ] += 1

    # ========================================================
    # STOP SESSION
    # ========================================================

    def stop_session(self):

        if not self.active:

            return None

        now = datetime.now()

        self.ended_at = (
            now.isoformat(
                timespec="seconds"
            )
        )

        session_data = {

            "session_id":
                self.session_id,

            "started_at":
                self.started_at,

            "ended_at":
                self.ended_at,

            "total_snapshots":
                len(
                    self.snapshots
                ),

            "students_seen":
                list(
                    self.students_seen.values()
                ),

            "snapshots":
                self.snapshots
        }

        filename = (
            self.session_id
            + ".json"
        )

        filepath = os.path.join(
            self.sessions_dir,
            filename
        )

        with open(
            filepath,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                session_data,
                file,
                indent=4
            )

        print()
        print("=" * 60)
        print("CLASSROOM SESSION STOPPED")
        print("=" * 60)
        print(f"Session ID : {self.session_id}")
        print(f"Started    : {self.started_at}")
        print(f"Ended      : {self.ended_at}")
        print(
            f"Snapshots  : {len(self.snapshots)}"
        )
        print(
            f"Students   : {len(self.students_seen)}"
        )
        print(f"Saved      : {filepath}")
        print("=" * 60)
        print()

        self.active = False

        result = filepath

        self.session_id = None

        self.started_at = None

        self.ended_at = None

        self.snapshots = []

        self.students_seen = {}

        return result

    # ========================================================
    # SESSION STATUS
    # ========================================================

    def get_status(self):

        return {

            "active":
                self.active,

            "session_id":
                self.session_id,

            "started_at":
                self.started_at,

            "ended_at":
                self.ended_at,

            "snapshots":
                len(
                    self.snapshots
                ),

            "students_seen":
                len(
                    self.students_seen
                )
        }