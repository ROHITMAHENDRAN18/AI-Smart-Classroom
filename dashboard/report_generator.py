import csv
import json
import os
import sys
from datetime import datetime


BASE_DIR = os.path.dirname(__file__)

SESSIONS_DIR = os.path.join(
    BASE_DIR,
    "sessions"
)

REPORTS_DIR = os.path.join(
    BASE_DIR,
    "reports"
)


os.makedirs(REPORTS_DIR, exist_ok=True)


def load_session(session_id):

    if not session_id:
        raise ValueError("Session ID is required")

    filename = session_id + ".json"

    filepath = os.path.join(
        SESSIONS_DIR,
        filename
    )

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Session not found: {session_id}"
        )

    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def calculate_statistics(session):

    snapshots = session.get(
        "snapshots",
        []
    )

    students_seen = session.get(
        "students_seen",
        []
    )

    tracked_values = []

    attentive = 0
    not_attentive = 0
    unknown = 0

    for snapshot in snapshots:

        tracked_persons = snapshot.get(
            "tracked_persons",
            0
        )

        try:
            tracked_persons = int(
                tracked_persons
            )
        except Exception:
            tracked_persons = 0

        tracked_values.append(
            tracked_persons
        )

        students = snapshot.get(
            "students",
            []
        )

        if not isinstance(
            students,
            list
        ):
            continue

        for student in students:

            if not isinstance(
                student,
                dict
            ):
                continue

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

    total_attention = (
        attentive
        + not_attentive
        + unknown
    )

    if total_attention > 0:

        attentive_rate = round(
            attentive
            / total_attention
            * 100,
            2
        )

        not_attentive_rate = round(
            not_attentive
            / total_attention
            * 100,
            2
        )

        unknown_rate = round(
            unknown
            / total_attention
            * 100,
            2
        )

    else:

        attentive_rate = 0
        not_attentive_rate = 0
        unknown_rate = 0

    duration_seconds = 0

    started_at = session.get(
        "started_at"
    )

    ended_at = session.get(
        "ended_at"
    )

    if started_at and ended_at:

        try:

            start_time = datetime.fromisoformat(
                started_at
            )

            end_time = datetime.fromisoformat(
                ended_at
            )

            duration_seconds = max(
                0,
                int(
                    (
                        end_time
                        - start_time
                    ).total_seconds()
                )
            )

        except Exception:

            duration_seconds = 0

    average_tracked = 0

    if tracked_values:

        average_tracked = round(
            sum(tracked_values)
            / len(tracked_values),
            2
        )

    maximum_tracked = 0

    if tracked_values:

        maximum_tracked = max(
            tracked_values
        )

    return {
        "duration_seconds": duration_seconds,
        "duration_minutes": round(
            duration_seconds / 60,
            2
        ),
        "total_snapshots": len(
            snapshots
        ),
        "unique_students": len(
            students_seen
        ),
        "average_tracked_persons":
            average_tracked,
        "maximum_tracked_persons":
            maximum_tracked,
        "attentive": attentive,
        "not_attentive": not_attentive,
        "unknown": unknown,
        "total_attention_observations":
            total_attention,
        "attentive_rate":
            attentive_rate,
        "not_attentive_rate":
            not_attentive_rate,
        "unknown_rate":
            unknown_rate
    }


def generate_html_report(
    session,
    statistics
):

    session_id = session.get(
        "session_id",
        "UNKNOWN"
    )

    students = session.get(
        "students_seen",
        []
    )

    started_at = session.get(
        "started_at",
        "-"
    )

    ended_at = session.get(
        "ended_at",
        "-"
    )

    student_rows = ""

    for student in students:

        student_id = student.get(
            "student_id",
            "UNKNOWN"
        )

        first_seen = student.get(
            "first_seen",
            "-"
        )

        last_seen = student.get(
            "last_seen",
            "-"
        )

        observations = student.get(
            "observations",
            0
        )

        student_rows += f"""
        <tr>
            <td>{student_id}</td>
            <td>{first_seen}</td>
            <td>{last_seen}</td>
            <td>{observations}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>
AI Smart Classroom Report
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{

    margin: 0;

    background: #070b12;

    color: #f5f7fa;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

}}

.container {{

    max-width: 1100px;

    margin: auto;

    padding: 40px 25px;

}}

.header {{

    background: #0d141f;

    border: 1px solid #202d3e;

    border-radius: 14px;

    padding: 25px;

    margin-bottom: 20px;

}}

.title {{

    font-size: 30px;

    font-weight: 700;

}}

.title span {{

    color: #00d9ff;

}}

.subtitle {{

    color: #8995a7;

    margin-top: 8px;

}}

.cards {{

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 14px;

    margin-bottom: 20px;

}}

.card {{

    background: #101722;

    border: 1px solid #202d3e;

    border-radius: 12px;

    padding: 20px;

}}

.label {{

    color: #8995a7;

    font-size: 12px;

}}

.value {{

    font-size: 26px;

    font-weight: 700;

    margin-top: 8px;

    color: #00d9ff;

}}

.panel {{

    background: #101722;

    border: 1px solid #202d3e;

    border-radius: 12px;

    padding: 22px;

    margin-bottom: 20px;

}}

.panel h2 {{

    margin-top: 0;

}}

.info-row {{

    display: flex;

    justify-content:
        space-between;

    padding: 12px 0;

    border-bottom:
        1px solid #1d2938;

}}

.green {{

    color: #4dff88;

}}

.red {{

    color: #ff6673;

}}

.gray {{

    color: #8995a7;

}}

.bar-container {{

    width: 100%;

    height: 18px;

    background: #1d2938;

    border-radius: 20px;

    overflow: hidden;

    margin:
        8px 0
        20px;

}}

.bar {{

    height: 100%;

}}

.bar-green {{

    background: #4dff88;

}}

.bar-red {{

    background: #ff6673;

}}

.bar-gray {{

    background: #718096;

}}

table {{

    width: 100%;

    border-collapse:
        collapse;

}}

th {{

    text-align: left;

    color: #8995a7;

    font-size: 12px;

    padding: 12px;

}}

td {{

    padding: 12px;

    border-top:
        1px solid #1d2938;

}}

.footer {{

    text-align: center;

    color: #667085;

    margin-top: 30px;

}}

@media(max-width: 800px) {{

    .cards {{

        grid-template-columns:
            repeat(2, 1fr);

    }}

}}

</style>

</head>

<body>

<div class="container">

<div class="header">

<div class="title">

AI SMART <span>CLASSROOM</span>

</div>

<div class="subtitle">

Classroom Session Report

</div>

</div>


<div class="panel">

<h2>Session Information</h2>

<div class="info-row">

<span>Session ID</span>

<strong>
{session_id}
</strong>

</div>

<div class="info-row">

<span>Started</span>

<strong>
{started_at}
</strong>

</div>

<div class="info-row">

<span>Ended</span>

<strong>
{ended_at}
</strong>

</div>

</div>


<div class="cards">

<div class="card">

<div class="label">
DURATION
</div>

<div class="value">
{statistics["duration_minutes"]} min
</div>

</div>


<div class="card">

<div class="label">
SNAPSHOTS
</div>

<div class="value">
{statistics["total_snapshots"]}
</div>

</div>


<div class="card">

<div class="label">
UNIQUE STUDENTS
</div>

<div class="value">
{statistics["unique_students"]}
</div>

</div>


<div class="card">

<div class="label">
MAX TRACKED
</div>

<div class="value">
{statistics["maximum_tracked_persons"]}
</div>

</div>

</div>


<div class="panel">

<h2>
Attention Analysis
</h2>


<div>

Attentive:
<strong class="green">
{statistics["attentive_rate"]}%
</strong>

</div>

<div class="bar-container">

<div
class="bar bar-green"
style="width:
{statistics["attentive_rate"]}%">
</div>

</div>


<div>

Not Attentive:
<strong class="red">
{statistics["not_attentive_rate"]}%
</strong>

</div>

<div class="bar-container">

<div
class="bar bar-red"
style="width:
{statistics["not_attentive_rate"]}%">
</div>

</div>


<div>

Unknown:
<strong class="gray">
{statistics["unknown_rate"]}%
</strong>

</div>

<div class="bar-container">

<div
class="bar bar-gray"
style="width:
{statistics["unknown_rate"]}%">
</div>

</div>

</div>


<div class="panel">

<h2>
Student Attendance / Observation Report
</h2>

<table>

<thead>

<tr>

<th>
Student ID
</th>

<th>
First Seen
</th>

<th>
Last Seen
</th>

<th>
Observations
</th>

</tr>

</thead>

<tbody>

{student_rows}

</tbody>

</table>

</div>


<div class="panel">

<h2>
Classroom Statistics
</h2>

<div class="info-row">

<span>
Average Tracked Persons
</span>

<strong>
{statistics["average_tracked_persons"]}
</strong>

</div>

<div class="info-row">

<span>
Maximum Tracked Persons
</span>

<strong>
{statistics["maximum_tracked_persons"]}
</strong>

</div>

<div class="info-row">

<span>
Total Attention Observations
</span>

<strong>
{statistics["total_attention_observations"]}
</strong>

</div>

</div>


<div class="footer">

AI Smart Classroom
|
Automated Classroom Monitoring Report

</div>

</div>

</body>

</html>
"""

    filename = (
        "REPORT_"
        + session_id
        + ".html"
    )

    filepath = os.path.join(
        REPORTS_DIR,
        filename
    )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)

    return filepath


def generate_csv_report(
    session,
    statistics
):

    session_id = session.get(
        "session_id",
        "UNKNOWN"
    )

    filename = (
        "REPORT_"
        + session_id
        + ".csv"
    )

    filepath = os.path.join(
        REPORTS_DIR,
        filename
    )

    students = session.get(
        "students_seen",
        []
    )

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Session ID",
            "Started At",
            "Ended At",
            "Duration Minutes",
            "Total Snapshots",
            "Unique Students",
            "Average Tracked Persons",
            "Maximum Tracked Persons",
            "Attentive Rate",
            "Not Attentive Rate",
            "Unknown Rate"
        ])

        writer.writerow([
            session_id,
            session.get(
                "started_at",
                ""
            ),
            session.get(
                "ended_at",
                ""
            ),
            statistics[
                "duration_minutes"
            ],
            statistics[
                "total_snapshots"
            ],
            statistics[
                "unique_students"
            ],
            statistics[
                "average_tracked_persons"
            ],
            statistics[
                "maximum_tracked_persons"
            ],
            statistics[
                "attentive_rate"
            ],
            statistics[
                "not_attentive_rate"
            ],
            statistics[
                "unknown_rate"
            ]
        ])

        writer.writerow([])

        writer.writerow([
            "Student ID",
            "First Seen",
            "Last Seen",
            "Observations"
        ])

        for student in students:

            writer.writerow([
                student.get(
                    "student_id",
                    "UNKNOWN"
                ),
                student.get(
                    "first_seen",
                    ""
                ),
                student.get(
                    "last_seen",
                    ""
                ),
                student.get(
                    "observations",
                    0
                )
            ])

    return filepath


def generate_report(session_id):

    session = load_session(
        session_id
    )

    statistics = calculate_statistics(
        session
    )

    html_path = generate_html_report(
        session,
        statistics
    )

    csv_path = generate_csv_report(
        session,
        statistics
    )

    return {
        "session_id": session_id,
        "html_report": html_path,
        "csv_report": csv_path,
        "statistics": statistics
    }


def main():

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            "python -m dashboard.report_generator "
            "<SESSION_ID>"
        )

        print()

        return

    session_id = sys.argv[1]

    try:

        result = generate_report(
            session_id
        )

        print()
        print("=" * 60)
        print("CLASSROOM REPORT GENERATED")
        print("=" * 60)

        print(
            f"Session ID : "
            f"{result['session_id']}"
        )

        print(
            f"HTML       : "
            f"{result['html_report']}"
        )

        print(
            f"CSV        : "
            f"{result['csv_report']}"
        )

        print()

        print(
            "Attention Rate : "
            f"{result['statistics']['attentive_rate']}%"
        )

        print(
            "Not Attentive  : "
            f"{result['statistics']['not_attentive_rate']}%"
        )

        print(
            "Unknown        : "
            f"{result['statistics']['unknown_rate']}%"
        )

        print("=" * 60)
        print()

    except Exception as error:

        print()
        print(
            f"Report generation failed: {error}"
        )
        print()


if __name__ == "__main__":
    main()