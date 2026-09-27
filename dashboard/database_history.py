import json
import urllib.error
import urllib.request


API_BASE_URL = "http://127.0.0.1:8000/api/v1"


def _request_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=3,
        ) as response:
            body = response.read().decode("utf-8")

        return json.loads(body)

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return None


def get_database_sessions(
    limit=50,
    offset=0,
):
    url = (
        f"{API_BASE_URL}/history/sessions"
        f"?limit={limit}&offset={offset}"
    )

    result = _request_json(url)

    if result is None:
        return []

    if not isinstance(result, list):
        return []

    return result


def get_database_session(
    session_id,
):
    url = (
        f"{API_BASE_URL}/history/sessions/"
        f"{session_id}"
    )

    return _request_json(url)


def get_database_attendance(
    session_id,
):
    url = (
        f"{API_BASE_URL}/history/sessions/"
        f"{session_id}/attendance"
    )

    result = _request_json(url)

    if result is None:
        return []

    if not isinstance(result, list):
        return []

    return result


def get_database_attention(
    session_id,
):
    url = (
        f"{API_BASE_URL}/history/sessions/"
        f"{session_id}/attention"
    )

    result = _request_json(url)

    if result is None:
        return []

    if not isinstance(result, list):
        return []

    return result


def get_database_session_summary(
    session_id,
):
    url = (
        f"{API_BASE_URL}/history/sessions/"
        f"{session_id}/summary"
    )

    return _request_json(url)


def get_database_history():
    sessions = get_database_sessions()

    return {
        "available": bool(sessions),
        "sessions": sessions,
    }