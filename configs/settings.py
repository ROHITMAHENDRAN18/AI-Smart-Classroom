import os

from dotenv import load_dotenv


load_dotenv()


def get_required(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set."
        )

    return value


def get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    return float(value)


def get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    return int(value)


PROJECT_NAME = os.getenv(
    "PROJECT_NAME",
    "AI Smart Classroom Attention Monitoring",
)

PROJECT_VERSION = os.getenv(
    "PROJECT_VERSION",
    "1.0.0",
)

HOST = os.getenv(
    "HOST",
    "127.0.0.1",
)

PORT = get_int(
    "PORT",
    8000,
)

DEBUG = get_bool(
    "DEBUG",
    True,
)

DATABASE_URL = get_required(
    "DATABASE_URL",
)

CAMERA_SOURCE = os.getenv(
    "CAMERA_SOURCE",
    "0",
)

ATTENDANCE_THRESHOLD = get_float(
    "ATTENDANCE_THRESHOLD",
    0.70,
)

ATTENTION_THRESHOLD = get_float(
    "ATTENTION_THRESHOLD",
    0.60,
)

API_VERSION = os.getenv(
    "API_VERSION",
    "/api/v1",
)

YOLO_MODEL = os.getenv(
    "YOLO_MODEL",
    "yolov8m.pt",
)

CAMERA_INDEX = get_int(
    "CAMERA_INDEX",
    0,
)

FACE_RECOGNITION_THRESHOLD = get_float(
    "FACE_RECOGNITION_THRESHOLD",
    0.50,
)

DASHBOARD_UPDATE_INTERVAL = get_float(
    "DASHBOARD_UPDATE_INTERVAL",
    0.5,
)

DATABASE_ATTENTION_UPDATE_INTERVAL = get_float(
    "DATABASE_ATTENTION_UPDATE_INTERVAL",
    1.0,
)

DASHBOARD_HOST = os.getenv(
    "DASHBOARD_HOST",
    "127.0.0.1",
)

DASHBOARD_PORT = get_int(
    "DASHBOARD_PORT",
    5050,
)

JWT_SECRET_KEY = get_required(
    "JWT_SECRET_KEY",
)