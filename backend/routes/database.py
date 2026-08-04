from fastapi import APIRouter
from sqlalchemy import text

from backend.database.connection import engine

router = APIRouter()


@router.get("/database")
def database_health():
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version();")
            ).scalar()

        return {
            "success": True,
            "database": "Connected",
            "version": version,
        }

    except Exception as e:
        return {
            "success": False,
            "database": "Disconnected",
            "error": str(e),
        }