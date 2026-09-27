"""Read-only schema and connectivity verification for Phase 18.11."""

from sqlalchemy import inspect, text

from backend.database.connection import engine


REQUIRED_TABLES = {
    "students",
    "classroom_sessions",
    "attendance_records",
    "attention_records",
}
REQUIRED_ATTENTION_COLUMNS = {
    "track_id",
    "attention_state",
    "attention_score",
    "fusion_state",
    "fusion_score",
    "fusion_confidence",
    "temporal_state",
    "temporal_score",
    "temporal_confidence",
    "temporal_stable",
    "recorded_at",
}


def main():
    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        missing_tables = REQUIRED_TABLES - tables
        if missing_tables:
            raise RuntimeError(
                "Missing required tables: " + ", ".join(sorted(missing_tables))
            )

        attention_columns = {
            column["name"]
            for column in inspector.get_columns("attention_records")
        }
        missing_columns = REQUIRED_ATTENTION_COLUMNS - attention_columns
        if missing_columns:
            raise RuntimeError(
                "Missing attention_records columns: "
                + ", ".join(sorted(missing_columns))
            )

        for table_name in sorted(REQUIRED_TABLES):
            print(f"OK table: {table_name}")
        for column_name in sorted(REQUIRED_ATTENTION_COLUMNS):
            print(f"OK attention_records.{column_name}")

        result = connection.execute(text("SELECT 1")).scalar_one()
        if result != 1:
            raise RuntimeError("Database connectivity check failed.")
        print("OK PostgreSQL connectivity")


if __name__ == "__main__":
    main()
