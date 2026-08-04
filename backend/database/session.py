from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal


def get_db():
    """
    Create a database session.

    Automatically closes the session
    after every request.
    """

    db: Session = SessionLocal()

    try:
        yield db

    finally:
        db.close()