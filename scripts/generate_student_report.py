import csv
import sys
from pathlib import Path

from sqlalchemy import text

from backend.database.connection import engine


REPORT_DIR = Path(
    "dashboard/reports/student"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def generate_student_report(
    student_id: str
):

    with engine.connect() as db:

        student_query = text(
            """
            SELECT
                student_id,
                name,
                department,
                year,
                section,
                email
            FROM students
            WHERE student_id = :student_id
            """
        )

        student = db.execute(
            student_query,
            {
                "student_id": student_id
            }
        ).mappings().first()

        if not student:
            raise ValueError(
                f"Student {student_id} not found"
            )

        analytics_query = text(
            """
            SELECT
                attention_state,
                attention_score,
                fusion_state,
                fusion_score,
                fusion_confidence,
                temporal_state,
                temporal_score,
                temporal_confidence,
                temporal_stable,
                recorded_at
            FROM attention_records
            WHERE student_id = :student_id
            ORDER BY recorded_at ASC
            """
        )

        records = db.execute(
            analytics_query,
            {
                "student_id": student_id
            }
        ).mappings().all()

    output_file = (
        REPORT_DIR /
        f"{student_id}_attention_report.csv"
    )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(
            file,
            lineterminator="\n"
        )

        writer.writerow(
            [
                "Student ID",
                "Name",
                "Department",
                "Year",
                "Section",
                "Email",
                "Recorded At",
                "Attention State",
                "Attention Score",
                "Fusion State",
                "Fusion Score",
                "Fusion Confidence",
                "Temporal State",
                "Temporal Score",
                "Temporal Confidence",
                "Temporal Stable",
            ]
        )

        for record in records:

            writer.writerow(
                [
                    student["student_id"],
                    student["name"],
                    student["department"],
                    student["year"],
                    student["section"],
                    student["email"],
                    record["recorded_at"],
                    record["attention_state"],
                    record["attention_score"],
                    record["fusion_state"],
                    record["fusion_score"],
                    record["fusion_confidence"],
                    record["temporal_state"],
                    record["temporal_score"],
                    record["temporal_confidence"],
                    record["temporal_stable"],
                ]
            )

    print("=" * 60)
    print("STUDENT REPORT GENERATED")
    print("=" * 60)
    print(f"Student : {student_id}")
    print(f"Records : {len(records)}")
    print(f"File    : {output_file}")
    print("=" * 60)

    return output_file


def main():

    if len(sys.argv) != 2:

        print(
            "Usage: "
            "python -m scripts.generate_student_report "
            "<student_id>"
        )

        raise SystemExit(1)

    student_id = sys.argv[1]

    generate_student_report(
        student_id
    )


if __name__ == "__main__":
    main()