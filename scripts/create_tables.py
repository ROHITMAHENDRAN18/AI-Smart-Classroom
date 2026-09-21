from backend.database.base import Base
from backend.database.connection import engine
from backend.models.student import Student

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")