import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

CSV_FILE = os.path.join(
    BASE_DIR,
    "attendance",
    "attendance.csv"
)


class AttendanceManager:

    def __init__(self):

        self.marked_students = set()

        if os.path.exists(CSV_FILE):

            with open(CSV_FILE, "r") as file:

                reader = csv.DictReader(file)

                for row in reader:

                    self.marked_students.add(
                        row["Student_ID"]
                    )

        else:

            with open(CSV_FILE, "w", newline="") as file:

                writer = csv.writer(file)

                writer.writerow(
                    [
                        "Student_ID",
                        "Date",
                        "Time",
                        "Status"
                    ]
                )

    def mark_attendance(self, student_id):

        if student_id in self.marked_students:

            return False

        now = datetime.now()

        date = now.strftime("%Y-%m-%d")

        time = now.strftime("%H:%M:%S")

        with open(CSV_FILE, "a", newline="") as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    student_id,
                    date,
                    time,
                    "Present"
                ]
            )

        self.marked_students.add(student_id)

        return True