from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.analytics.student_analytics import (
    calculate_attendance_analytics,
    calculate_attention_analytics,
)


# ============================================================
# TOTAL CLASSROOM SESSIONS
# ============================================================

def get_total_sessions(
    db: Session
) -> int:

    query = text(
        """
        SELECT COUNT(*)
        FROM classroom_sessions
        """
    )

    return int(
        db.execute(query).scalar() or 0
    )


# ============================================================
# STUDENT ATTENDED SESSIONS
# ============================================================

def get_student_attended_sessions(
    db: Session,
    student_id: str
) -> int:

    query = text(
        """
        SELECT COUNT(DISTINCT session_id)
        FROM attendance_records
        WHERE student_id = :student_id
        AND LOWER(status) = 'present'
        """
    )

    return int(
        db.execute(
            query,
            {
                "student_id": student_id
            }
        ).scalar() or 0
    )


# ============================================================
# STUDENT INFORMATION
# ============================================================

def get_student_info(
    db: Session,
    student_id: str
):

    query = text(
        """
        SELECT
            student_id,
            name
        FROM students
        WHERE student_id = :student_id
        LIMIT 1
        """
    )

    row = db.execute(
        query,
        {
            "student_id": student_id
        }
    ).mappings().first()

    if not row:
        return None

    return dict(row)


# ============================================================
# STUDENT ATTENTION RECORDS
# ============================================================

def get_student_attention_records(
    db: Session,
    student_id: str
):

    query = text(
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

    rows = db.execute(
        query,
        {
            "student_id": student_id
        }
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# STUDENT ANALYTICS
# ============================================================

def get_student_analytics(
    db: Session,
    student_id: str
):

    student = get_student_info(
        db,
        student_id
    )

    total_sessions = get_total_sessions(
        db
    )

    attended_sessions = (
        get_student_attended_sessions(
            db,
            student_id
        )
    )

    records = get_student_attention_records(
        db,
        student_id
    )

    attendance = calculate_attendance_analytics(
        student_id=student_id,
        total_sessions=total_sessions,
        attended_sessions=attended_sessions
    )

    attention = calculate_attention_analytics(
        student_id=student_id,
        records=records
    )

    return {
        "student_id": student_id,
        "student_name": (
            student["name"]
            if student
            else None
        ),
        "attendance": attendance,
        "attention": attention,
    }


# ============================================================
# ALL STUDENTS ANALYTICS
# ============================================================

def get_all_students_analytics(
    db: Session
):

    query = text(
        """
        SELECT student_id
        FROM students
        ORDER BY student_id
        """
    )

    students = db.execute(
        query
    ).mappings().all()

    return [
        get_student_analytics(
            db,
            student["student_id"]
        )
        for student in students
    ]


# ============================================================
# STUDENT ATTENTION TIMELINE
# ============================================================

def get_student_attention_timeline(
    db: Session,
    student_id: str
):

    query = text(
        """
        SELECT
            recorded_at,
            attention_state,
            attention_score,
            fusion_state,
            fusion_score,
            temporal_state,
            temporal_score,
            temporal_confidence,
            temporal_stable
        FROM attention_records
        WHERE student_id = :student_id
        ORDER BY recorded_at ASC
        """
    )

    rows = db.execute(
        query,
        {
            "student_id": student_id
        }
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# CLASSROOM ANALYTICS
# ============================================================

def get_classroom_analytics(db: Session):
    query = text("""
        SELECT
            COUNT(*) AS total_records,

            AVG(
                CASE
                    WHEN attention_score > 1
                        THEN attention_score / 100.0
                    ELSE attention_score
                END
            ) AS average_attention_score,

            COUNT(*) FILTER (
                WHERE REPLACE(
                    UPPER(attention_state),
                    ' ',
                    ''
                ) = 'ATTENTIVE'
            ) AS attentive_records,

            COUNT(*) FILTER (
                WHERE REPLACE(
                    UPPER(attention_state),
                    ' ',
                    ''
                ) = 'PARTIAL'
            ) AS partial_records,

            COUNT(*) FILTER (
                WHERE REPLACE(
                    UPPER(attention_state),
                    ' ',
                    ''
                ) = 'NOTATTENTIVE'
            ) AS not_attentive_records,

            COUNT(*) FILTER (
                WHERE attention_state IS NULL
                   OR REPLACE(
                        UPPER(attention_state),
                        ' ',
                        ''
                   ) = 'UNKNOWN'
            ) AS unknown_records

        FROM attention_records
    """)

    row = db.execute(query).mappings().first()

    if not row:
        return {
            "total_records": 0,
            "average_attention_score": 0.0,
            "attention_percentage": 0.0,
            "attentive_records": 0,
            "partial_records": 0,
            "not_attentive_records": 0,
            "unknown_records": 0,
        }

    average_score = float(
        row["average_attention_score"] or 0.0
    )

    return {
        "total_records": int(
            row["total_records"] or 0
        ),

        "average_attention_score": round(
            average_score,
            4
        ),

        "attention_percentage": round(
            average_score * 100,
            2
        ),

        "attentive_records": int(
            row["attentive_records"] or 0
        ),

        "partial_records": int(
            row["partial_records"] or 0
        ),

        "not_attentive_records": int(
            row["not_attentive_records"] or 0
        ),

        "unknown_records": int(
            row["unknown_records"] or 0
        ),
    }