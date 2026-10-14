"""Safely add the session/student attendance uniqueness constraint.

The migration refuses to delete or merge attendance history. If legacy
duplicates exist, it prints the affected keys and exits so an administrator
can review and resolve them before rerunning.
"""

from sqlalchemy import create_engine, inspect, text

from configs.settings import DATABASE_URL


TABLE = "attendance_records"
CONSTRAINT = "uq_attendance_session_student"


def migrate() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table(TABLE):
                raise RuntimeError(f"Required table {TABLE!r} does not exist")

            constraints = inspector.get_unique_constraints(TABLE)
            if any(
                set(item.get("column_names") or [])
                == {"session_id", "student_id"}
                for item in constraints
            ):
                print(
                    "A unique constraint for session_id/student_id already "
                    "exists; nothing to do."
                )
                return

            duplicates = connection.execute(
                text(
                    "SELECT session_id, student_id, COUNT(*) AS row_count "
                    "FROM attendance_records "
                    "GROUP BY session_id, student_id HAVING COUNT(*) > 1 "
                    "ORDER BY session_id, student_id"
                )
            ).mappings().all()
            if duplicates:
                details = ", ".join(
                    f"({item['session_id']}, {item['student_id']}): "
                    f"{item['row_count']} rows"
                    for item in duplicates
                )
                raise RuntimeError(
                    "Attendance duplicates need teacher/admin review before "
                    f"the unique constraint can be applied: {details}"
                )

            if connection.dialect.name == "postgresql":
                connection.execute(
                    text(
                        "ALTER TABLE attendance_records ADD CONSTRAINT "
                        "uq_attendance_session_student UNIQUE "
                        "(session_id, student_id)"
                    )
                )
            elif connection.dialect.name == "sqlite":
                raise RuntimeError(
                    "This production migration targets PostgreSQL. For a "
                    "SQLite development database, rebuild only the local "
                    "attendance_records table from the current SQLAlchemy "
                    "metadata after making a backup."
                )
            else:
                raise RuntimeError(
                    f"Unsupported migration dialect: {connection.dialect.name}"
                )
        print(f"Added {CONSTRAINT}; no attendance rows were removed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate()
