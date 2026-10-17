
from backend.database.base import Base
from backend.database.connection import engine

# Import all models so SQLAlchemy registers their tables.
from backend.models import (
    Student,
    ClassroomSession,
    AttendanceRecord,
    AttentionRecord,
    User,
    Teacher,
    Classroom,
    ClassroomMember,
    FrameInferenceSummary,
)


def create_tables():
    print("Checking and creating missing database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database table creation completed.")
    print("Existing tables and records have not been intentionally deleted.")


if __name__ == "__main__":
    create_tables()
