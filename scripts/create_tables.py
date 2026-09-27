from backend.database.base import Base
from backend.database.connection import engine

from backend.models.student import Student
from backend.models.classroom_session import ClassroomSession
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord


print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")