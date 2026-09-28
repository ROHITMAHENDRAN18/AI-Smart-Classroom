import json
from urllib.request import urlopen
from urllib.error import URLError


FASTAPI_BASE_URL = "http://127.0.0.1:8000/api/v1"


def fetch_json(path):

    url = (
        f"{FASTAPI_BASE_URL}"
        f"{path}"
    )

    try:

        with urlopen(
            url,
            timeout=5
        ) as response:

            data = response.read()

            return json.loads(
                data.decode("utf-8")
            )

    except (
        URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError
    ) as error:

        return {
            "success": False,
            "error": str(error)
        }


def get_classroom_analytics():

    return fetch_json(
        "/analytics/classroom"
    )


def get_students_analytics():

    return fetch_json(
        "/analytics/students"
    )


def get_student_analytics(student_id):

    return fetch_json(
        f"/analytics/students/{student_id}"
    )


def get_student_timeline(student_id):

    return fetch_json(
        f"/analytics/students/{student_id}/timeline"
    )