"""Additive PostgreSQL migration for Phase 18.11 attention metadata."""

from sqlalchemy import inspect, text

from backend.database.connection import engine


TABLE_NAME = "attention_records"
COLUMNS = {
    "attention_score": "DOUBLE PRECISION",
    "fusion_state": "VARCHAR(32)",
    "fusion_score": "DOUBLE PRECISION",
    "fusion_confidence": "DOUBLE PRECISION",
    "temporal_state": "VARCHAR(32)",
    "temporal_score": "DOUBLE PRECISION",
    "temporal_confidence": "DOUBLE PRECISION",
    "temporal_stable": "BOOLEAN",
}


def migrate():
    """Add missing nullable fields; preserve all existing records and fields."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table(TABLE_NAME):
            raise RuntimeError(f"Required table {TABLE_NAME!r} does not exist.")

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(TABLE_NAME)
        }
        preparer = connection.dialect.identifier_preparer
        quoted_table = preparer.quote(TABLE_NAME)

        for column_name, column_type in COLUMNS.items():
            if column_name in existing_columns:
                print(f"SKIP {column_name} (already exists)")
                continue

            quoted_column = preparer.quote(column_name)
            connection.execute(
                text(
                    f"ALTER TABLE {quoted_table} "
                    f"ADD COLUMN IF NOT EXISTS {quoted_column} {column_type}"
                )
            )
            print(f"ADD {column_name} ({column_type}, nullable)")

        migrated_columns = {
            column["name"]
            for column in inspect(connection).get_columns(TABLE_NAME)
        }
        missing = set(COLUMNS) - migrated_columns
        if missing:
            raise RuntimeError(
                "Migration incomplete; missing columns: "
                + ", ".join(sorted(missing))
            )

    print("Phase 18.11 migration completed; existing data was not dropped.")


if __name__ == "__main__":
    migrate()
