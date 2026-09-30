from backend.database.base import Base
from backend.database.connection import engine

from backend.models import (
    Student,
    ClassroomSession,
    AttendanceRecord,
    AttentionRecord,
    User,
    Teacher,
    Classroom,
    ClassroomMember,
)


def create_tables():
    print("Creating database tables...")

    Base.metadata.create_all(
        bind=engine
    )

    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()