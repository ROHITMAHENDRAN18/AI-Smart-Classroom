"""Make students.email nullable to allow optional email enrollment."""

from sqlalchemy import create_engine, inspect, text

from configs.settings import DATABASE_URL

TABLE = "students"
COLUMN = "email"


def migrate() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table(TABLE):
                raise RuntimeError(f"Required table {TABLE!r} does not exist")
            columns = {column["name"]: column for column in inspector.get_columns(TABLE)}
            if COLUMN not in columns:
                raise RuntimeError(f"Column {COLUMN!r} does not exist in table {TABLE!r}")
            
            if columns[COLUMN].get("nullable", True):
                print(f"{TABLE}.{COLUMN} is already nullable; nothing to do.")
                return

            if connection.dialect.name != "postgresql":
                raise RuntimeError(
                    "This migration targets PostgreSQL; no schema was changed."
                )

            connection.execute(
                text("ALTER TABLE students ALTER COLUMN email DROP NOT NULL;")
            )
        print(f"Successfully made {TABLE}.{COLUMN} nullable.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate()
