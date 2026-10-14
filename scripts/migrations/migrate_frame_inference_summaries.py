"""Create the bounded, image-free per-session frame summary table."""

from sqlalchemy import create_engine, inspect, text

from configs.settings import DATABASE_URL


def migrate() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if inspector.has_table("frame_inference_summaries"):
                columns = {
                    column["name"]
                    for column in inspector.get_columns("frame_inference_summaries")
                }
                required_columns = {
                    "id",
                    "session_id",
                    "classroom_id",
                    "latest_frame_received_at",
                    "latest_processed_at",
                    "frame_width",
                    "frame_height",
                    "detection_count",
                    "detections",
                    "frames_processed",
                    "updated_at",
                }
                missing_columns = required_columns - columns
                if missing_columns:
                    raise RuntimeError(
                        "frame_inference_summaries exists but is incomplete; "
                        "missing columns: " + ", ".join(sorted(missing_columns))
                    )
                if "inference_duration_ms" not in columns:
                    connection.execute(
                        text(
                            "ALTER TABLE frame_inference_summaries ADD COLUMN "
                            "inference_duration_ms DOUBLE PRECISION NOT NULL "
                            "DEFAULT 0"
                        )
                    )
                    print("Added inference_duration_ms to existing summaries.")
                if "face_detections" not in columns:
                    connection.execute(
                        text(
                            "ALTER TABLE frame_inference_summaries ADD COLUMN "
                            "face_detections JSONB NOT NULL DEFAULT '[]'::jsonb"
                        )
                    )
                    print("Added bounded face_detections summary column.")
                if "face_detection_status" not in columns:
                    connection.execute(
                        text(
                            "ALTER TABLE frame_inference_summaries ADD COLUMN "
                            "face_detection_status VARCHAR(20) NOT NULL DEFAULT 'error'"
                        )
                    )
                    print("Added face_detection_status summary column.")
                unique_session = any(
                    set(constraint.get("column_names") or []) == {"session_id"}
                    for constraint in inspector.get_unique_constraints(
                        "frame_inference_summaries"
                    )
                )
                foreign_keys = inspector.get_foreign_keys("frame_inference_summaries")
                has_session_fk = any(
                    item.get("constrained_columns") == ["session_id"]
                    and item.get("referred_table") == "classroom_sessions"
                    and item.get("referred_columns") == ["session_id"]
                    for item in foreign_keys
                )
                has_classroom_fk = any(
                    item.get("constrained_columns") == ["classroom_id"]
                    and item.get("referred_table") == "classrooms"
                    and item.get("referred_columns") == ["id"]
                    for item in foreign_keys
                )
                has_classroom_index = any(
                    item.get("column_names") == ["classroom_id"]
                    for item in inspector.get_indexes("frame_inference_summaries")
                )
                if not (
                    unique_session
                    and has_session_fk
                    and has_classroom_fk
                    and has_classroom_index
                ):
                    raise RuntimeError(
                        "frame_inference_summaries is missing its session "
                        "uniqueness, foreign-key, or classroom-index constraint. "
                        "Review the schema before applying a corrective migration."
                    )
                print("frame_inference_summaries already exists; nothing to do.")
                return
            if not inspector.has_table("classroom_sessions"):
                raise RuntimeError("Required table 'classroom_sessions' is missing")
            if not inspector.has_table("classrooms"):
                raise RuntimeError("Required table 'classrooms' is missing")

            connection.execute(
                text(
                    "CREATE TABLE frame_inference_summaries ("
                    "id SERIAL PRIMARY KEY, "
                    "session_id VARCHAR(100) NOT NULL UNIQUE REFERENCES "
                    "classroom_sessions(session_id) ON DELETE CASCADE, "
                    "classroom_id INTEGER NOT NULL REFERENCES "
                    "classrooms(id) ON DELETE CASCADE, "
                    "latest_frame_received_at TIMESTAMP WITH TIME ZONE NOT NULL, "
                    "latest_processed_at TIMESTAMP WITH TIME ZONE NOT NULL, "
                    "frame_width INTEGER NOT NULL, "
                    "frame_height INTEGER NOT NULL, "
                    "detection_count INTEGER NOT NULL, "
                    "inference_duration_ms DOUBLE PRECISION NOT NULL, "
                    "detections JSONB NOT NULL, "
                    "face_detections JSONB NOT NULL DEFAULT '[]'::jsonb, "
                    "face_detection_status VARCHAR(20) NOT NULL DEFAULT 'error', "
                    "frames_processed INTEGER NOT NULL DEFAULT 1, "
                    "updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"
                    ")"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX ix_frame_inference_summaries_classroom_id "
                    "ON frame_inference_summaries (classroom_id)"
                )
            )
        print("Created frame_inference_summaries; no images were stored.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate()
