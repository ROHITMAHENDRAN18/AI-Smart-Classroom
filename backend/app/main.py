from fastapi import FastAPI
from backend.utils.logger import logger
from backend.exceptions.handlers import generic_exception_handler
from backend.routes.database import router as database_router
from backend.routes.students import router as student_router

from configs.config import (
    PROJECT_NAME,
    PROJECT_VERSION,
    API_VERSION,
)

from backend.routes.health import router as health_router

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description="Backend API for AI Smart Classroom",
)
app.add_exception_handler(Exception, generic_exception_handler)
logger.info("AI Smart Classroom Backend Started Successfully")

app.include_router(
    health_router,
    prefix=API_VERSION,
    tags=["Health"]
)
app.include_router(
    database_router,
    prefix=API_VERSION,
    tags=["Database"]
)
app.include_router(
    student_router,
    prefix=API_VERSION,
)


@app.get("/")
def home():
    return {
        "message": f"Welcome to {PROJECT_NAME}",
        "status": "Backend Running",
        "version": PROJECT_VERSION,
    }
