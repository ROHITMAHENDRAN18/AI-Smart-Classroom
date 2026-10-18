import os

from dotenv import load_dotenv

load_dotenv()


def get_required(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set.")

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


def get_bounded_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = get_int(name, default)
    if not minimum <= value <= maximum:
        raise RuntimeError(
            f"Environment variable '{name}' must be between "
            f"{minimum} and {maximum}."
        )
    return value


def get_bounded_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    value = get_float(name, default)
    if not minimum <= value <= maximum:
        raise RuntimeError(
            f"Environment variable '{name}' must be between "
            f"{minimum} and {maximum}."
        )
    return value


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

ATTENTION_MINIMUM_SAMPLES = get_bounded_int(
    "ATTENTION_MINIMUM_SAMPLES",
    3,
    2,
    10,
)

ATTENTION_MINIMUM_DURATION_SECONDS = get_bounded_float(
    "ATTENTION_MINIMUM_DURATION_SECONDS",
    4.0,
    0.0,
    60.0,
)

FRAME_MAX_PAYLOAD_BYTES = get_bounded_int(
    "FRAME_MAX_PAYLOAD_BYTES",
    2 * 1024 * 1024,
    1024,
    10 * 1024 * 1024,
)

FRAME_MAX_WIDTH = get_bounded_int(
    "FRAME_MAX_WIDTH",
    1920,
    320,
    4096,
)

FRAME_MAX_HEIGHT = get_bounded_int(
    "FRAME_MAX_HEIGHT",
    1920,
    320,
    4096,
)

FRAME_MAX_PIXELS = get_bounded_int(
    "FRAME_MAX_PIXELS",
    2_073_600,
    102_400,
    16_777_216,
)

FRAME_MIN_INTERVAL_SECONDS = get_bounded_float(
    "FRAME_MIN_INTERVAL_SECONDS",
    1.5,
    0.25,
    60.0,
)

FRAME_INFERENCE_TIMEOUT_SECONDS = get_bounded_float(
    "FRAME_INFERENCE_TIMEOUT_SECONDS",
    30.0,
    1.0,
    300.0,
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
