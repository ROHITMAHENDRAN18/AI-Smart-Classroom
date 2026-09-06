import csv
import os
from datetime import datetime


class AttendanceManager:

    def __init__(self):

        print("=" * 70)
        print("Loading Attendance Manager...")
        print("=" * 70)

        self.attendance_file = "attendance/attendance.csv"

        self.present_students = set()

        os.makedirs(
            "attendance",
            exist_ok=True
        )

        print("Attendance Manager Loaded Successfully.")
        print(
            f"Attendance file: {self.attendance_file}"
        )
        print("=" * 70)

    # ========================================================
    # MARK STUDENT PRESENT
    # ========================================================

    def mark_present(
        self,
        student_id,
        track_id,
        similarity
    ):
        """
        Mark a recognized student as present.

        A student is recorded only once
        during the current program session.
        """

        # ----------------------------------------------------
        # Prevent duplicate attendance
        # ----------------------------------------------------

        if student_id in self.present_students:

            return False

        # ----------------------------------------------------
        # Current date and time
        # ----------------------------------------------------

        now = datetime.now()

        date = now.strftime(
            "%Y-%m-%d"
        )

        time = now.strftime(
            "%H:%M:%S"
        )

        # ----------------------------------------------------
        # Check whether CSV already exists
        # ----------------------------------------------------

        file_exists = os.path.exists(
            self.attendance_file
        )

        # ----------------------------------------------------
        # Write attendance record
        # ----------------------------------------------------

        with open(
            self.attendance_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            # Header
            if not file_exists:

                writer.writerow(
                    [
                        "student_id",
                        "track_id",
                        "similarity",
                        "date",
                        "time",
                        "status"
                    ]
                )

            # Attendance record
            writer.writerow(
                [
                    student_id,
                    track_id,
                    f"{similarity:.3f}",
                    date,
                    time,
                    "Present"
                ]
            )

        # ----------------------------------------------------
        # Store in memory
        # ----------------------------------------------------

        self.present_students.add(
            student_id
        )

        print(
            f"[ATTENDANCE] "
            f"{student_id} marked PRESENT "
            f"(Track ID: {track_id}, "
            f"Similarity: {similarity:.3f})"
        )

        return True

    # ========================================================
    # CHECK WHETHER STUDENT IS PRESENT
    # ========================================================

    def is_present(
        self,
        student_id
    ):
        """
        Check whether a student has already
        been marked present in this session.
        """

        return student_id in self.present_students

    # ========================================================
    # GET PRESENT STUDENTS
    # ========================================================

    def get_present_students(self):

        return sorted(
            self.present_students
        )

    # ========================================================
    # GET PRESENT COUNT
    # ========================================================

    def get_present_count(self):

        return len(
            self.present_students
        )