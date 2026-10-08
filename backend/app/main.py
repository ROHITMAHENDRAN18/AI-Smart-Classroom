from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.exceptions.handlers import generic_exception_handler
from backend.routes.analytics import router as analytics_router
from backend.routes.database import router as database_router
from backend.routes.health import router as health_router
from backend.routes.history import router as history_router
from backend.routes.auth import router as auth_router
from backend.routes.students import router as student_router
from backend.utils.logger import logger
from backend.routes.teacher import router as teacher_router
from backend.routes.classrooms import router as classroom_router
from backend.routes.classroom_members import (
    router as classroom_member_router,
)
from backend.routes.classroom_sessions import (
    router as classroom_session_router,
)
from backend.routes.classroom_overview import (
    router as classroom_overview_router,
)

from configs.config import (
    API_VERSION,
    PROJECT_NAME,
    PROJECT_VERSION,
)


app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description="Backend API for AI Smart Classroom",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)


logger.info(
    "AI Smart Classroom Backend Started Successfully"
)


app.include_router(
    health_router,
    prefix=API_VERSION,
    tags=["Health"],
)


app.include_router(
    database_router,
    prefix=API_VERSION,
    tags=["Database"],
)


app.include_router(
    student_router,
    prefix=API_VERSION,
)


app.include_router(
    history_router,
    prefix=API_VERSION,
)


app.include_router(
    analytics_router,
    prefix=API_VERSION,
)


app.include_router(
    auth_router,
    prefix=API_VERSION,
)
app.include_router(
    teacher_router,
    prefix=API_VERSION,
)
app.include_router(
    classroom_router,
    prefix=API_VERSION,
)
app.include_router(
    classroom_member_router,
    prefix=API_VERSION,
)
app.include_router(
    classroom_session_router,
    prefix=API_VERSION,
)

app.include_router(
    classroom_overview_router,
    prefix=API_VERSION,
    tags=["Classroom Overview"],
)

@app.get("/")
def home():
    return {
        "message": f"Welcome to {PROJECT_NAME}",
        "status": "Backend Running",
        "version": PROJECT_VERSION,
    }