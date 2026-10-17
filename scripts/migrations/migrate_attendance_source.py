"""Add nullable provenance to attendance rows without rewriting history."""

from sqlalchemy import create_engine, inspect, text

from configs.settings import DATABASE_URL


TABLE = "attendance_records"
COLUMN = "attendance_source"


def migrate() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table(TABLE):
                raise RuntimeError(f"Required table {TABLE!r} does not exist")
            columns = {column["name"] for column in inspector.get_columns(TABLE)}
            if COLUMN in columns:
                print(f"{TABLE}.{COLUMN} already exists; nothing to do.")
                return
            if connection.dialect.name != "postgresql":
                raise RuntimeError(
                    "This migration targets PostgreSQL; no schema was changed."
                )
            connection.execute(
                text(
                    "ALTER TABLE attendance_records "
                    "ADD COLUMN attendance_source VARCHAR(20) NULL"
                )
            )
        print(
            "Added nullable attendance_source. Existing rows remain NULL because "
            "their source cannot be established from stored data."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate()
