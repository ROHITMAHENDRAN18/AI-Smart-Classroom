from dotenv import load_dotenv
import os


load_dotenv()


def get_required(name):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        raise ValueError(
            f"CONFIGURATION ERROR: Required environment variable '{name}' is missing."
        )

    return value.strip()


def get_int(name, minimum=None, maximum=None):
    value = get_required(name)

    try:
        result = int(value)
    except ValueError:
        raise ValueError(
            f"CONFIGURATION ERROR: '{name}' must be an integer. "
            f"Current value: {value}"
        )

    if minimum is not None and result < minimum:
        raise ValueError(
            f"CONFIGURATION ERROR: '{name}' must be >= {minimum}. "
            f"Current value: {result}"
        )

    if maximum is not None and result > maximum:
        raise ValueError(
            f"CONFIGURATION ERROR: '{name}' must be <= {maximum}. "
            f"Current value: {result}"
        )

    return result


def get_float(name, minimum=None, maximum=None, exclusive_minimum=False):
    value = get_required(name)

    try:
        result = float(value)
    except ValueError:
        raise ValueError(
            f"CONFIGURATION ERROR: '{name}' must be a number. "
            f"Current value: {value}"
        )

    if minimum is not None:
        if exclusive_minimum and result <= minimum:
            raise ValueError(
                f"CONFIGURATION ERROR: '{name}' must be > {minimum}. "
                f"Current value: {result}"
            )

        if not exclusive_minimum and result < minimum:
            raise ValueError(
                f"CONFIGURATION ERROR: '{name}' must be >= {minimum}. "
                f"Current value: {result}"
            )

    if maximum is not None and result > maximum:
        raise ValueError(
            f"CONFIGURATION ERROR: '{name}' must be <= {maximum}. "
            f"Current value: {result}"
        )

    return result


def get_bool(name):
    value = get_required(name).lower()

    if value == "true":
        return True

    if value == "false":
        return False

    raise ValueError(
        f"CONFIGURATION ERROR: '{name}' must be True or False. "
        f"Current value: {value}"
    )


PROJECT_NAME = get_required("PROJECT_NAME")
PROJECT_VERSION = get_required("PROJECT_VERSION")
API_VERSION = get_required("API_VERSION")

HOST = get_required("HOST")

PORT = get_int(
    "PORT",
    minimum=1,
    maximum=65535
)

DEBUG = get_bool("DEBUG")

DATABASE_URL = get_required("DATABASE_URL")

CAMERA_SOURCE = get_int(
    "CAMERA_SOURCE",
    minimum=0
)

ATTENDANCE_THRESHOLD = get_float(
    "ATTENDANCE_THRESHOLD",
    minimum=0.0,
    maximum=1.0
)

ATTENTION_THRESHOLD = get_float(
    "ATTENTION_THRESHOLD",
    minimum=0.0,
    maximum=1.0
)

YOLO_MODEL = get_required("YOLO_MODEL")

CAMERA_INDEX = get_int(
    "CAMERA_INDEX",
    minimum=0
)

FACE_RECOGNITION_THRESHOLD = get_float(
    "FACE_RECOGNITION_THRESHOLD",
    minimum=0.0,
    maximum=1.0
)

DASHBOARD_UPDATE_INTERVAL = get_float(
    "DASHBOARD_UPDATE_INTERVAL",
    minimum=0.0,
    exclusive_minimum=True
)

DASHBOARD_HOST = get_required("DASHBOARD_HOST")

DASHBOARD_PORT = get_int(
    "DASHBOARD_PORT",
    minimum=1,
    maximum=65535
)