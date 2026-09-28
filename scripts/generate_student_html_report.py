import sys
from pathlib import Path
from html import escape

from sqlalchemy import text

from backend.database.connection import engine


REPORT_DIR = Path("dashboard/reports/student")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def format_value(value, suffix=""):
    if value is None:
        return "—"

    return f"{value}{suffix}"


def normalize_attention_score(score):
    if score is None:
        return None

    try:
        score = float(score)
    except (TypeError, ValueError):
        return None

    if score > 1.0:
        score = score / 100.0

    return max(0.0, min(1.0, score))


def normalize_state(state):
    if not state:
        return "UNKNOWN"

    state = str(state).strip().upper()
    state = state.replace("_", " ")

    if state == "NOTATTENTIVE":
        return "NOT ATTENTIVE"

    return state


def get_student_data(student_id):
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
            LIMIT 1
            """
        )

        student = db.execute(
            student_query,
            {"student_id": student_id}
        ).mappings().first()

        if not student:
            return None, [], 0, 0

        attendance_query = text(
            """
            SELECT COUNT(DISTINCT session_id)
            FROM attendance_records
            WHERE student_id = :student_id
            AND LOWER(status) = 'present'
            """
        )

        attended_sessions = int(
            db.execute(
                attendance_query,
                {"student_id": student_id}
            ).scalar()
            or 0
        )

        total_sessions_query = text(
            """
            SELECT COUNT(*)
            FROM classroom_sessions
            """
        )

        total_sessions = int(
            db.execute(total_sessions_query).scalar()
            or 0
        )

        records_query = text(
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
            records_query,
            {"student_id": student_id}
        ).mappings().all()

    return (
        dict(student),
        [dict(record) for record in records],
        attended_sessions,
        total_sessions
    )


def calculate_attention_summary(records):

    attentive = 0
    partial = 0
    not_attentive = 0
    unknown = 0

    scores = []

    for record in records:

        state = normalize_state(
            record.get("attention_state")
        )

        if state == "ATTENTIVE":
            attentive += 1

        elif state == "PARTIAL":
            partial += 1

        elif state == "NOT ATTENTIVE":
            not_attentive += 1

        else:
            unknown += 1

        score = normalize_attention_score(
            record.get("attention_score")
        )

        if score is not None:
            scores.append(score)

    average_score = (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )

    return {
        "attentive": attentive,
        "partial": partial,
        "not_attentive": not_attentive,
        "unknown": unknown,
        "average_score": average_score,
        "percentage": average_score * 100,
    }


def build_html(
    student,
    records,
    attended_sessions,
    total_sessions
):

    attention = calculate_attention_summary(records)

    attendance_percentage = (
        attended_sessions / total_sessions * 100
        if total_sessions > 0
        else 0.0
    )

    student_id = escape(
        str(student["student_id"])
    )

    student_name = escape(
        str(student["name"])
    )

    department = escape(
        str(student["department"])
    )

    section = escape(
        str(student["section"])
    )

    email = escape(
        str(student["email"])
    )

    year = escape(
        str(student["year"])
    )

    rows = []

    for record in records:

        score = normalize_attention_score(
            record.get("attention_score")
        )

        score_display = (
            f"{score * 100:.2f}%"
            if score is not None
            else "—"
        )

        state = normalize_state(
            record.get("attention_state")
        )

        fusion_state = normalize_state(
            record.get("fusion_state")
        )

        temporal_state = normalize_state(
            record.get("temporal_state")
        )

        fusion_score = record.get(
            "fusion_score"
        )

        temporal_score = record.get(
            "temporal_score"
        )

        fusion_display = (
            f"{float(fusion_score) * 100:.2f}%"
            if fusion_score is not None
            else "—"
        )

        temporal_display = (
            f"{float(temporal_score) * 100:.2f}%"
            if temporal_score is not None
            else "—"
        )

        stable = record.get(
            "temporal_stable"
        )

        stable_display = (
            "YES"
            if stable is True
            else "NO"
            if stable is False
            else "—"
        )

        recorded_at = escape(
            str(record.get("recorded_at") or "—")
        )

        rows.append(
            f"""
            <tr>
                <td>{recorded_at}</td>
                <td>{escape(state)}</td>
                <td>{score_display}</td>
                <td>{escape(fusion_state)}</td>
                <td>{fusion_display}</td>
                <td>{escape(temporal_state)}</td>
                <td>{temporal_display}</td>
                <td>{stable_display}</td>
            </tr>
            """
        )

    timeline_rows = "".join(rows)

    generated_at = escape(
        __import__("datetime")
        .datetime.now()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
Student Attention Report - {student_id}
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 0;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background:
        #f4f7fb;
    color: #172033;
}}

.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 40px 24px;
}}

.header {{
    background:
        linear-gradient(
            135deg,
            #182848,
            #4b3f9f
        );
    color: white;
    padding: 40px;
    border-radius: 24px;
    margin-bottom: 24px;
}}

.header h1 {{
    margin: 0 0 10px;
    font-size: 34px;
}}

.header p {{
    margin: 5px 0;
    opacity: 0.9;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 18px;
    margin-bottom: 24px;
}}

.card {{
    background: white;
    border-radius: 18px;
    padding: 24px;
    box-shadow:
        0 8px 30px rgba(20, 30, 60, 0.08);
}}

.card h3 {{
    margin: 0 0 10px;
    color: #64748b;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

.metric {{
    font-size: 32px;
    font-weight: 700;
}}

.info {{
    display: grid;
    grid-template-columns:
        repeat(2, minmax(0, 1fr));
    gap: 12px;
}}

.info div {{
    padding: 14px;
    background: #f8fafc;
    border-radius: 12px;
}}

.info strong {{
    display: block;
    margin-bottom: 4px;
}}

.section {{
    background: white;
    border-radius: 18px;
    padding: 24px;
    margin-top: 24px;
    box-shadow:
        0 8px 30px rgba(20, 30, 60, 0.08);
}}

.section h2 {{
    margin-top: 0;
}}

.table-wrapper {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 950px;
}}

th,
td {{
    text-align: left;
    padding: 12px 14px;
    border-bottom: 1px solid #e5e7eb;
}}

th {{
    background: #f8fafc;
    font-size: 13px;
    color: #475569;
}}

.footer {{
    text-align: center;
    margin-top: 30px;
    color: #64748b;
    font-size: 13px;
}}

@media (max-width: 900px) {{

    .grid {{
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }}

}}

@media (max-width: 600px) {{

    .container {{
        padding: 20px 12px;
    }}

    .header {{
        padding: 24px;
    }}

    .header h1 {{
        font-size: 26px;
    }}

    .grid {{
        grid-template-columns: 1fr;
    }}

    .info {{
        grid-template-columns: 1fr;
    }}

}}

</style>
</head>

<body>

<div class="container">

<header class="header">

<h1>
AI Smart Classroom
</h1>

<p>
Student Attention & Analytics Report
</p>

<p>
Generated: {generated_at}
</p>

</header>


<section class="section">

<h2>Student Information</h2>

<div class="info">

<div>
<strong>Student ID</strong>
{student_id}
</div>

<div>
<strong>Name</strong>
{student_name}
</div>

<div>
<strong>Department</strong>
{department}
</div>

<div>
<strong>Year</strong>
{year}
</div>

<div>
<strong>Section</strong>
{section}
</div>

<div>
<strong>Email</strong>
{email}
</div>

</div>

</section>


<section class="grid">

<div class="card">
<h3>Attendance</h3>
<div class="metric">
{attendance_percentage:.2f}%
</div>
<p>
{attended_sessions}
/
{total_sessions}
sessions
</p>
</div>

<div class="card">
<h3>Average Attention</h3>
<div class="metric">
{attention["percentage"]:.2f}%
</div>
<p>
Average normalized attention score
</p>
</div>

<div class="card">
<h3>Attentive Records</h3>
<div class="metric">
{attention["attentive"]}
</div>
<p>
Monitoring records
</p>
</div>

<div class="card">
<h3>Not Attentive</h3>
<div class="metric">
{attention["not_attentive"]}
</div>
<p>
Monitoring records
</p>
</div>

</section>


<section class="section">

<h2>Attention Summary</h2>

<div class="grid">

<div class="card">
<h3>Attentive</h3>
<div class="metric">
{attention["attentive"]}
</div>
</div>

<div class="card">
<h3>Partial</h3>
<div class="metric">
{attention["partial"]}
</div>
</div>

<div class="card">
<h3>Not Attentive</h3>
<div class="metric">
{attention["not_attentive"]}
</div>
</div>

<div class="card">
<h3>Unknown</h3>
<div class="metric">
{attention["unknown"]}
</div>
</div>

</div>

</section>


<section class="section">

<h2>Attention Timeline</h2>

<div class="table-wrapper">

<table>

<thead>

<tr>
<th>Recorded At</th>
<th>Attention State</th>
<th>Attention Score</th>
<th>Fusion State</th>
<th>Fusion Score</th>
<th>Temporal State</th>
<th>Temporal Score</th>
<th>Stable</th>
</tr>

</thead>

<tbody>

{timeline_rows}

</tbody>

</table>

</div>

</section>


<div class="footer">

AI Smart Classroom Attention Monitoring

</div>

</div>

</body>
</html>
"""


def generate_student_html_report(student_id):

    (
        student,
        records,
        attended_sessions,
        total_sessions
    ) = get_student_data(student_id)

    if not student:
        raise ValueError(
            f"Student {student_id} not found"
        )

    html = build_html(
        student,
        records,
        attended_sessions,
        total_sessions
    )

    output_file = (
        REPORT_DIR
        / f"{student_id}_attention_report.html"
    )

    output_file.write_text(
        html,
        encoding="utf-8"
    )

    print("=" * 60)
    print("HTML STUDENT REPORT GENERATED")
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
            "python -m scripts.generate_student_html_report "
            "<student_id>"
        )

        raise SystemExit(1)

    student_id = sys.argv[1]

    generate_student_html_report(
        student_id
    )


if __name__ == "__main__":
    main()