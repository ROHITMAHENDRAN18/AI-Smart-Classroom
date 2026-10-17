"""Add a session-level unknown face detection counter."""

from sqlalchemy import create_engine, inspect, text

from configs.settings import DATABASE_URL


TABLE = "frame_inference_summaries"
COLUMN = "unknown_detections"


def migrate() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table(TABLE):
                raise RuntimeError(f"Required table {TABLE!r} does not exist.")
            if connection.dialect.name != "postgresql":
                raise RuntimeError(
                    "This migration targets PostgreSQL; no schema was changed."
                )
            columns = {column["name"] for column in inspector.get_columns(TABLE)}
            if COLUMN in columns:
                print(f"{TABLE}.{COLUMN} already exists; nothing to do.")
                return
            connection.execute(
                text(
                    "ALTER TABLE frame_inference_summaries "
                    "ADD COLUMN unknown_detections INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            )
        print(
            "Added unknown_detections. Existing summaries start at zero "
            "because historical unknown detections cannot be reconstructed."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate()
