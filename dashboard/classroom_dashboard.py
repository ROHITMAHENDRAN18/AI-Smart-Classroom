import json
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dashboard.session_manager import ClassroomSessionManager
from dashboard.alert_manager import ClassroomAlertManager
from configs.settings import DASHBOARD_HOST, DASHBOARD_PORT
from dashboard.camera_stream import CameraStream


HOST = DASHBOARD_HOST
PORT = DASHBOARD_PORT

BASE_DIR = os.path.dirname(__file__)

STATE_FILE = os.path.join(
    BASE_DIR,
    "classroom_state.json"
)

SESSIONS_DIR = os.path.join(
    BASE_DIR,
    "sessions"
)

DEFAULT_STATE = {
    "timestamp": "Waiting for STEP 9...",
    "tracked_persons": 0,
    "present_students": 0,
    "students": []
}


SESSION_MANAGER = None
ALERT_MANAGER = None
CAMERA_STREAM = CameraStream()


def load_state():

    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception as error:

        print(
            f"State read error: {error}"
        )

    return DEFAULT_STATE.copy()


def load_session(session_id):

    if not session_id:
        return None

    filename = session_id + ".json"

    filepath = os.path.join(
        SESSIONS_DIR,
        filename
    )

    if not os.path.exists(filepath):
        return None

    try:

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"Session read error: {error}"
        )

        return None


def list_sessions():

    os.makedirs(
        SESSIONS_DIR,
        exist_ok=True
    )

    sessions = []

    for filename in os.listdir(
        SESSIONS_DIR
    ):

        if not filename.startswith(
            "SESSION_"
        ):
            continue

        if not filename.endswith(
            ".json"
        ):
            continue

        filepath = os.path.join(
            SESSIONS_DIR,
            filename
        )

        try:

            with open(
                filepath,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            sessions.append({

                "session_id":
                    data.get(
                        "session_id",
                        filename.replace(
                            ".json",
                            ""
                        )
                    ),

                "started_at":
                    data.get(
                        "started_at"
                    ),

                "ended_at":
                    data.get(
                        "ended_at"
                    ),

                "total_snapshots":
                    data.get(
                        "total_snapshots",
                        0
                    ),

                "students_count":
                    len(
                        data.get(
                            "students_seen",
                            []
                        )
                    )
            })

        except Exception:

            continue

    sessions.sort(
        key=lambda item:
            item.get("started_at") or "",
        reverse=True
    )

    return sessions


def calculate_analytics(session):

    if not session:

        return {
            "session_id": None,
            "duration_seconds": 0,
            "duration_minutes": 0,
            "total_snapshots": 0,
            "unique_students": 0,
            "average_tracked_persons": 0,
            "maximum_tracked_persons": 0,
            "attention": {
                "attentive": 0,
                "not_attentive": 0,
                "unknown": 0,
                "total": 0,
                "attentive_rate": 0,
                "not_attentive_rate": 0,
                "unknown_rate": 0
            },
            "students": [],
            "timeline": []
        }

    snapshots = session.get(
        "snapshots",
        []
    )

    students_seen = session.get(
        "students_seen",
        []
    )

    tracked_values = []

    attentive_count = 0
    not_attentive_count = 0
    unknown_count = 0

    timeline = []

    for snapshot in snapshots:

        tracked = snapshot.get(
            "tracked_persons",
            0
        )

        try:

            tracked = int(
                tracked
            )

        except Exception:

            tracked = 0

        tracked_values.append(
            tracked
        )

        students = snapshot.get(
            "students",
            []
        )

        snapshot_attentive = 0
        snapshot_not_attentive = 0
        snapshot_unknown = 0

        if isinstance(
            students,
            list
        ):

            for student in students:

                if not isinstance(
                    student,
                    dict
                ):
                    continue

                attention = str(
                    student.get(
                        "attention",
                        "UNKNOWN"
                    )
                ).upper()

                if attention == "ATTENTIVE":

                    attentive_count += 1
                    snapshot_attentive += 1

                elif attention == "NOT ATTENTIVE":

                    not_attentive_count += 1
                    snapshot_not_attentive += 1

                else:

                    unknown_count += 1
                    snapshot_unknown += 1

        timeline.append({

            "timestamp":
                snapshot.get(
                    "timestamp"
                ),

            "tracked_persons":
                tracked,

            "attentive":
                snapshot_attentive,

            "not_attentive":
                snapshot_not_attentive,

            "unknown":
                snapshot_unknown
        })

    total_attention = (
        attentive_count
        + not_attentive_count
        + unknown_count
    )

    if total_attention > 0:

        attentive_rate = round(
            attentive_count
            / total_attention
            * 100,
            2
        )

        not_attentive_rate = round(
            not_attentive_count
            / total_attention
            * 100,
            2
        )

        unknown_rate = round(
            unknown_count
            / total_attention
            * 100,
            2
        )

    else:

        attentive_rate = 0
        not_attentive_rate = 0
        unknown_rate = 0

    duration_seconds = 0

    started_at = session.get(
        "started_at"
    )

    ended_at = session.get(
        "ended_at"
    )

    if started_at and ended_at:

        try:

            start_time = datetime.fromisoformat(
                started_at
            )

            end_time = datetime.fromisoformat(
                ended_at
            )

            duration_seconds = max(
                0,
                int(
                    (
                        end_time
                        - start_time
                    ).total_seconds()
                )
            )

        except Exception:

            duration_seconds = 0

    average_tracked = 0

    if tracked_values:

        average_tracked = round(
            sum(tracked_values)
            / len(tracked_values),
            2
        )

    maximum_tracked = (
        max(tracked_values)
        if tracked_values
        else 0
    )

    return {

        "session_id":
            session.get(
                "session_id"
            ),

        "started_at":
            started_at,

        "ended_at":
            ended_at,

        "duration_seconds":
            duration_seconds,

        "duration_minutes":
            round(
                duration_seconds / 60,
                2
            ),

        "total_snapshots":
            len(snapshots),

        "unique_students":
            len(students_seen),

        "average_tracked_persons":
            average_tracked,

        "maximum_tracked_persons":
            maximum_tracked,

        "attention": {

            "attentive":
                attentive_count,

            "not_attentive":
                not_attentive_count,

            "unknown":
                unknown_count,

            "total":
                total_attention,

            "attentive_rate":
                attentive_rate,

            "not_attentive_rate":
                not_attentive_rate,

            "unknown_rate":
                unknown_rate
        },

        "students":
            students_seen,

        "timeline":
            timeline
    }


DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html>

<head>

    <meta charset="UTF-8">

    <title>
        AI Smart Classroom
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {

            margin: 0;

            background:
                #070b12;

            color:
                #f5f7fa;

            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }

        header {

            height: 72px;

            display: flex;

            align-items: center;

            justify-content:
                space-between;

            padding:
                0 24px;

            background:
                #0c121c;

            border-bottom:
                1px solid #1d2938;
        }

        .brand {

            font-size:
                18px;

            font-weight:
                700;
        }

        .brand span {

            color:
                #00d9ff;
        }

        .live {

            color:
                #4dff88;

            font-size:
                13px;

            font-weight:
                700;
        }

        .container {

            max-width:
                1100px;

            margin:
                0 auto;

            padding:
                28px 20px;
        }

        h1 {

            margin:
                0;

            font-size:
                28px;
        }

        .subtitle {

            margin-top:
                8px;

            color:
                #8995a7;
        }

        .nav {

            display:
                flex;

            gap:
                10px;

            margin:
                22px 0;
        }

        .nav a {

            text-decoration:
                none;

            color:
                #cbd5e1;

            background:
                #101824;

            border:
                1px solid #243142;

            padding:
                10px 15px;

            border-radius:
                8px;
        }

        .nav a:hover {

            border-color:
                #00d9ff;

            color:
                #00d9ff;
        }

        .cards {

            display:
                grid;

            grid-template-columns:
                repeat(4, 1fr);

            gap:
                12px;

            margin-top:
                22px;
        }

        .card {

            background:
                #101722;

            border:
                1px solid #202d3e;

            border-radius:
                12px;

            padding:
                18px;
        }

        .label {

            color:
                #8995a7;

            font-size:
                12px;
        }

        .value {

            font-size:
                28px;

            font-weight:
                700;

            margin-top:
                8px;
        }

        .cyan {

            color:
                #00d9ff;
        }

        .green {

            color:
                #4dff88;
        }

        .red {

            color:
                #ff6673;
        }

        .grid {

            display:
                grid;

            grid-template-columns:
                1.6fr 1fr;

            gap:
                14px;

            margin-top:
                16px;
        }

        .panel {

            background:
                #101722;

            border:
                1px solid #202d3e;

            border-radius:
                12px;

            overflow:
                hidden;
        }

        .panel-title {

            padding:
                17px;

            border-bottom:
                1px solid #202d3e;

            font-weight:
                700;
        }

        .panel-body {

            padding:
                18px;
        }

        table {

            width:
                100%;

            border-collapse:
                collapse;
        }

        th {

            text-align:
                left;

            color:
                #8995a7;

            font-size:
                11px;

            padding:
                10px;
        }

        td {

            padding:
                12px 10px;

            border-top:
                1px solid #1b2634;

            font-size:
                13px;
        }

        .bar {

            height:
                9px;

            background:
                #1e2a39;

            border-radius:
                20px;

            overflow:
                hidden;

            margin:
                8px 0 16px;
        }

        .fill {

            height:
                100%;
        }

        .fill.green {

            background:
                #4dff88;
        }

        .fill.red {

            background:
                #ff6673;
        }

        .fill.gray {

            background:
                #718096;
        }

        .status {

            display:
                flex;

            justify-content:
                space-between;

            padding:
                12px;

            margin-top:
                10px;

            background:
                #0c131d;

            border:
                1px solid #202d3e;

            border-radius:
                8px;
        }

        .alerts-panel {

            margin-top:
                16px;

            background:
                #101722;

            border:
                1px solid #202d3e;

            border-radius:
                12px;

            overflow:
                hidden;
        }

        .alerts-header {

            display:
                flex;

            justify-content:
                space-between;

            align-items:
                center;

            padding:
                17px;

            border-bottom:
                1px solid #202d3e;
        }

        .alert-count {

            background:
                #ff6673;

            color:
                white;

            min-width:
                26px;

            height:
                26px;

            display:
                flex;

            align-items:
                center;

            justify-content:
                center;

            border-radius:
                50%;

            font-size:
                12px;

            font-weight:
                700;
        }

        .alerts-body {

            padding:
                15px;
        }

        .alert-item {

            display:
                flex;

            justify-content:
                space-between;

            gap:
                15px;

            padding:
                14px;

            margin-bottom:
                10px;

            background:
                #171d27;

            border:
                1px solid #3b2730;

            border-left:
                4px solid #ff6673;

            border-radius:
                8px;
        }

        .alert-info {

            flex:
                1;
        }

        .alert-title {

            font-weight:
                700;

            color:
                #ff6673;

            margin-bottom:
                5px;
        }

        .alert-message {

            font-size:
                13px;

            color:
                #d4d9e1;
        }

        .alert-time {

            font-size:
                11px;

            color:
                #8995a7;

            margin-top:
                6px;
        }

        .alert-actions {

            display:
                flex;

            gap:
                7px;

            align-items:
                center;
        }

        .alert-button {

            border:
                1px solid #334155;

            background:
                #111827;

            color:
                #cbd5e1;

            padding:
                7px 10px;

            border-radius:
                6px;

            cursor:
                pointer;

            font-size:
                11px;
        }

        .alert-button:hover {

            border-color:
                #00d9ff;

            color:
                #00d9ff;
        }

        .no-alerts {

            padding:
                20px;

            text-align:
                center;

            color:
                #8995a7;
        }

        .alert-stats {

            display:
                flex;

            gap:
                18px;

            color:
                #8995a7;

            font-size:
                12px;
        }

        @media(max-width: 800px) {

            .cards {

                grid-template-columns:
                    repeat(2, 1fr);
            }

            .grid {

                grid-template-columns:
                    1fr;
            }

            .alert-item {

                flex-direction:
                    column;
            }

            .alert-actions {

                justify-content:
                    flex-start;
            }
        }

    </style>

</head>

<body>

<header>

    <div class="brand">
        AI SMART <span>CLASSROOM</span>
    </div>

    <div class="live">
        ● LIVE
    </div>

</header>

<div class="container">

    <h1>
        Classroom Dashboard
    </h1>

    <div class="subtitle">
        Real-time student attendance and attention monitoring
    </div>

    <div class="nav">

        <a href="/">
            Live Dashboard
        </a>

        <a href="/analytics">
            Historical Analytics
        </a>

    </div>

    <div class="cards">

        <div class="card">

            <div class="label">
                TRACKED PERSONS
            </div>

            <div
                id="tracked"
                class="value cyan">
                0
            </div>

        </div>

        <div class="card">

            <div class="label">
                PRESENT STUDENTS
            </div>

            <div
                id="present"
                class="value green">
                0
            </div>

        </div>

        <div class="card">

            <div class="label">
                ATTENTIVE
            </div>

            <div
                id="attentive"
                class="value green">
                0
            </div>

        </div>

        <div class="card">

            <div class="label">
                NOT ATTENTIVE
            </div>

            <div
                id="notAttentive"
                class="value red">
                0
            </div>

        </div>

    </div>



    <div
        class="panel"
        style="
            margin-top: 16px;
        "
    >

        <div class="panel-title">
            Live Camera Feed
        </div>

        <div
            class="panel-body"
            style="
                padding: 0;
                background: #05080d;
            "
        >

            <img
                src="/video"
                alt="Live classroom camera"
                style="
                    display: block;
                    width: 100%;
                    height: auto;
                    min-height: 360px;
                    max-height: 620px;
                    object-fit: contain;
                    background: #05080d;
                "
            >

        </div>

    </div>


    <div class="alerts-panel">

        <div class="alerts-header">

            <div>

                <strong>
                    Classroom Alerts
                </strong>

                <div class="alert-stats">

                    <span>
                        Total:
                        <span id="totalAlerts">
                            0
                        </span>
                    </span>

                    <span>
                        Active:
                        <span id="activeAlerts">
                            0
                        </span>
                    </span>

                </div>

            </div>

            <div
                id="alertCount"
                class="alert-count">
                0
            </div>

        </div>

        <div
            id="alerts"
            class="alerts-body">

            <div class="no-alerts">
                No active alerts
            </div>

        </div>

    </div>


    <div class="grid">

        <div class="panel">

            <div class="panel-title">
                Live Student Monitoring
            </div>

            <div class="panel-body">

                <table>

                    <thead>

                        <tr>

                            <th>
                                TRACK
                            </th>

                            <th>
                                STUDENT
                            </th>

                            <th>
                                CONFIDENCE
                            </th>

                            <th>
                                ATTENTION
                            </th>

                        </tr>

                    </thead>

                    <tbody id="students">
                    </tbody>

                </table>

            </div>

        </div>


        <div class="panel">

            <div class="panel-title">
                Classroom Analytics
            </div>

            <div class="panel-body">

                <div>
                    Attention Rate
                </div>

                <div id="attentionText">
                    0%
                </div>

                <div class="bar">

                    <div
                        id="attentionBar"
                        class="fill green"
                        style="width:0%">
                    </div>

                </div>


                <div>
                    Not Attention Rate
                </div>

                <div id="notAttentionText">
                    0%
                </div>

                <div class="bar">

                    <div
                        id="notAttentionBar"
                        class="fill red"
                        style="width:0%">
                    </div>

                </div>


                <div>
                    Unknown / Processing
                </div>

                <div id="unknownText">
                    0%
                </div>

                <div class="bar">

                    <div
                        id="unknownBar"
                        class="fill gray"
                        style="width:0%">
                    </div>

                </div>


                <div class="status">

                    <span>
                        System
                    </span>

                    <span class="green">
                        ACTIVE
                    </span>

                </div>


                <div class="status">

                    <span>
                        Camera
                    </span>

                    <span class="green">
                        MONITORING
                    </span>

                </div>


                <div class="status">

                    <span>
                        Last Update
                    </span>

                    <span id="lastUpdate">
                        --
                    </span>

                </div>

            </div>

        </div>

    </div>

</div>


<script>


async function updateDashboard() {

    try {

        const response =
            await fetch(
                "/api/state?t=" +
                Date.now()
            );

        const data =
            await response.json();


        document.getElementById(
            "tracked"
        ).textContent =
            data.tracked_persons || 0;


        document.getElementById(
            "present"
        ).textContent =
            data.present_students || 0;


        let attentive = 0;

        let notAttentive = 0;

        let unknown = 0;


        const students =
            data.students || [];


        students.forEach(
            student => {

                const attention =
                    String(
                        student.attention ||
                        "UNKNOWN"
                    ).toUpperCase();


                if (
                    attention ===
                    "ATTENTIVE"
                ) {

                    attentive++;

                }
                else if (
                    attention ===
                    "NOT ATTENTIVE"
                ) {

                    notAttentive++;

                }
                else {

                    unknown++;

                }

            }
        );


        document.getElementById(
            "attentive"
        ).textContent =
            attentive;


        document.getElementById(
            "notAttentive"
        ).textContent =
            notAttentive;


        const total =
            attentive
            + notAttentive
            + unknown;


        let attentiveRate = 0;

        let notAttentiveRate = 0;

        let unknownRate = 0;


        if (total > 0) {

            attentiveRate =
                attentive /
                total *
                100;

            notAttentiveRate =
                notAttentive /
                total *
                100;

            unknownRate =
                unknown /
                total *
                100;

        }


        document.getElementById(
            "attentionText"
        ).textContent =
            attentiveRate.toFixed(0)
            + "%";


        document.getElementById(
            "notAttentionText"
        ).textContent =
            notAttentiveRate.toFixed(0)
            + "%";


        document.getElementById(
            "unknownText"
        ).textContent =
            unknownRate.toFixed(0)
            + "%";


        document.getElementById(
            "attentionBar"
        ).style.width =
            attentiveRate +
            "%";


        document.getElementById(
            "notAttentionBar"
        ).style.width =
            notAttentiveRate +
            "%";


        document.getElementById(
            "unknownBar"
        ).style.width =
            unknownRate +
            "%";


        const table =
            document.getElementById(
                "students"
            );


        table.innerHTML = "";


        students.forEach(
            student => {

                const row =
                    document.createElement(
                        "tr"
                    );


                const similarity =
                    Number(
                        student.similarity || 0
                    );


                const confidence =
                    similarity > 1
                        ? similarity
                        : similarity * 100;


                row.innerHTML = `

                    <td>
                        #${student.track_id ?? "-"}
                    </td>

                    <td>
                        ${student.student_id || "UNKNOWN"}
                    </td>

                    <td>
                        ${confidence.toFixed(1)}%
                    </td>

                    <td>
                        ${student.attention || "UNKNOWN"}
                    </td>

                `;


                table.appendChild(
                    row
                );

            }
        );


        document.getElementById(
            "lastUpdate"
        ).textContent =
            data.timestamp || "--";


    }
    catch (error) {

        console.error(
            "Dashboard update error:",
            error
        );

    }

}


async function updateAlerts() {

    try {

        const response =
            await fetch(
                "/api/alerts?t=" +
                Date.now()
            );


        const data =
            await response.json();


        const alerts =
            data.alerts || [];


        const statistics =
            data.statistics || {};


        const activeAlerts =
            alerts.filter(
                alert =>
                    alert.status === "ACTIVE"
            );


        document.getElementById(
            "alertCount"
        ).textContent =
            activeAlerts.length;


        document.getElementById(
            "totalAlerts"
        ).textContent =
            statistics.total || 0;


        document.getElementById(
            "activeAlerts"
        ).textContent =
            statistics.active || 0;


        const container =
            document.getElementById(
                "alerts"
            );


        if (activeAlerts.length === 0) {

            container.innerHTML = `

                <div class="no-alerts">
                    ✓ No active alerts
                </div>

            `;

            return;

        }


        container.innerHTML = "";


        activeAlerts.forEach(
            alert => {

                const item =
                    document.createElement(
                        "div"
                    );


                item.className =
                    "alert-item";


                item.innerHTML = `

                    <div class="alert-info">

                        <div class="alert-title">

                            ⚠
                            ${alert.alert_type}

                        </div>

                        <div class="alert-message">

                            ${alert.message}

                        </div>

                        <div class="alert-time">

                            ${alert.timestamp}

                            |
                            Track:
                            ${alert.track_id ?? "-"}

                        </div>

                    </div>


                    <div class="alert-actions">

                        <button
                            class="alert-button"
                            onclick="acknowledgeAlert(
                                '${alert.alert_id}'
                            )">

                            Acknowledge

                        </button>


                        <button
                            class="alert-button"
                            onclick="clearAlert(
                                '${alert.alert_id}'
                            )">

                            Clear

                        </button>

                    </div>

                `;


                container.appendChild(
                    item
                );

            }
        );


    }
    catch (error) {

        console.error(
            "Alert update error:",
            error
        );

    }

}


async function acknowledgeAlert(
    alertId
) {

    try {

        const response =
            await fetch(
                "/api/alerts/acknowledge?alert_id="
                + encodeURIComponent(
                    alertId
                )
            );


        const data =
            await response.json();


        if (!data.success) {

            console.error(
                "Unable to acknowledge alert"
            );

        }


        await updateAlerts();

    }
    catch (error) {

        console.error(
            "Acknowledge error:",
            error
        );

    }

}


async function clearAlert(
    alertId
) {

    try {

        const response =
            await fetch(
                "/api/alerts/clear?alert_id="
                + encodeURIComponent(
                    alertId
                )
            );


        const data =
            await response.json();


        if (!data.success) {

            console.error(
                "Unable to clear alert"
            );

        }


        await updateAlerts();

    }
    catch (error) {

        console.error(
            "Clear alert error:",
            error
        );

    }

}


updateDashboard();

updateAlerts();


setInterval(
    updateDashboard,
    1000
);


setInterval(
    updateAlerts,
    1000
);


</script>

</body>

</html>
"""


ANALYTICS_HTML = r"""
<!DOCTYPE html>
<html>

<head>

    <meta charset="UTF-8">

    <title>
        Historical Analytics - AI Smart Classroom
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {

            margin: 0;

            background:
                #070b12;

            color:
                #f5f7fa;

            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }

        header {

            height: 72px;

            display:
                flex;

            align-items:
                center;

            justify-content:
                space-between;

            padding:
                0 24px;

            background:
                #0c121c;

            border-bottom:
                1px solid #1d2938;
        }

        .brand {

            font-weight:
                700;

            font-size:
                18px;
        }

        .brand span {

            color:
                #00d9ff;
        }

        .container {

            max-width:
                1100px;

            margin:
                auto;

            padding:
                30px 20px;
        }

        h1 {

            margin-bottom:
                5px;
        }

        .subtitle {

            color:
                #8995a7;
        }

        a {

            color:
                #00d9ff;

            text-decoration:
                none;
        }

        select {

            margin-top:
                22px;

            width:
                100%;

            padding:
                13px;

            background:
                #101722;

            color:
                white;

            border:
                1px solid #273548;

            border-radius:
                8px;
        }

        .cards {

            display:
                grid;

            grid-template-columns:
                repeat(4, 1fr);

            gap:
                14px;

            margin-top:
                20px;
        }

        .card {

            background:
                #101722;

            border:
                1px solid #202d3e;

            border-radius:
                12px;

            padding:
                20px;
        }

        .label {

            color:
                #8995a7;

            font-size:
                12px;
        }

        .value {

            font-size:
                28px;

            margin-top:
                8px;

            font-weight:
                700;

            color:
                #00d9ff;
        }

        .panel {

            margin-top:
                18px;

            background:
                #101722;

            border:
                1px solid #202d3e;

            border-radius:
                12px;

            padding:
                20px;
        }

        .bar {

            height:
                18px;

            background:
                #1d2938;

            border-radius:
                20px;

            overflow:
                hidden;

            margin:
                8px 0 18px;
        }

        .fill {

            height:
                100%;
        }

        .green {

            background:
                #4dff88;
        }

        .red {

            background:
                #ff6673;
        }

        .gray {

            background:
                #718096;
        }

        .timeline {

            max-height:
                350px;

            overflow-y:
                auto;
        }

        .timeline-row {

            display:
                grid;

            grid-template-columns:
                180px 1fr 100px;

            gap:
                15px;

            padding:
                12px;

            border-bottom:
                1px solid #1c2735;
        }

        @media(max-width: 800px) {

            .cards {

                grid-template-columns:
                    repeat(2, 1fr);
            }

            .timeline-row {

                grid-template-columns:
                    1fr;
            }

        }

    </style>

</head>

<body>

<header>

    <div class="brand">
        AI SMART <span>CLASSROOM</span>
    </div>

    <a href="/">
        ← Live Dashboard
    </a>

</header>

<div class="container">

    <h1>
        Historical Session Analytics
    </h1>

    <div class="subtitle">
        Analyze previously recorded classroom sessions
    </div>

    <select id="sessionSelect">

        <option value="">
            Select a classroom session
        </option>

    </select>

    <div id="analyticsContent">

        <div class="panel">

            Select a session to view
            historical analytics.

        </div>

    </div>

</div>

<script>


async function loadSessions() {

    const response =
        await fetch(
            "/api/sessions"
        );


    const sessions =
        await response.json();


    const select =
        document.getElementById(
            "sessionSelect"
        );


    sessions.forEach(
        session => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                session.session_id;


            option.textContent =
                session.session_id
                +
                " | "
                +
                (
                    session.started_at
                    ||
                    "Unknown"
                );


            select.appendChild(
                option
            );

        }
    );

}


async function loadAnalytics(
    sessionId
) {

    if (!sessionId) {
        return;
    }


    const response =
        await fetch(
            "/api/analytics?session_id="
            +
            encodeURIComponent(
                sessionId
            )
        );


    const data =
        await response.json();


    if (data.error) {

        document.getElementById(
            "analyticsContent"
        ).innerHTML =
            `<div class="panel">
                ${data.error}
            </div>`;

        return;

    }


    const attention =
        data.attention;


    document.getElementById(
        "analyticsContent"
    ).innerHTML = `

        <div class="cards">

            <div class="card">

                <div class="label">
                    DURATION
                </div>

                <div class="value">
                    ${data.duration_minutes}
                    min
                </div>

            </div>


            <div class="card">

                <div class="label">
                    SNAPSHOTS
                </div>

                <div class="value">
                    ${data.total_snapshots}
                </div>

            </div>


            <div class="card">

                <div class="label">
                    UNIQUE STUDENTS
                </div>

                <div class="value">
                    ${data.unique_students}
                </div>

            </div>


            <div class="card">

                <div class="label">
                    AVG TRACKED
                </div>

                <div class="value">
                    ${data.average_tracked_persons}
                </div>

            </div>

        </div>


        <div class="panel">

            <h2>
                Attention Analysis
            </h2>


            <p>

                Attentive:

                <strong>
                    ${attention.attentive_rate}%
                </strong>

            </p>


            <div class="bar">

                <div
                    class="fill green"
                    style="
                        width:
                        ${attention.attentive_rate}%
                    "
                >
                </div>

            </div>


            <p>

                Not Attentive:

                <strong>
                    ${attention.not_attentive_rate}%
                </strong>

            </p>


            <div class="bar">

                <div
                    class="fill red"
                    style="
                        width:
                        ${attention.not_attentive_rate}%
                    "
                >
                </div>

            </div>


            <p>

                Unknown:

                <strong>
                    ${attention.unknown_rate}%
                </strong>

            </p>


            <div class="bar">

                <div
                    class="fill gray"
                    style="
                        width:
                        ${attention.unknown_rate}%
                    "
                >
                </div>

            </div>

        </div>


        <div class="panel">

            <h2>
                Session Information
            </h2>


            <p>

                <strong>
                    Session:
                </strong>

                ${data.session_id}

            </p>


            <p>

                <strong>
                    Started:
                </strong>

                ${data.started_at || "-"}

            </p>


            <p>

                <strong>
                    Ended:
                </strong>

                ${data.ended_at || "-"}

            </p>


            <p>

                <strong>
                    Maximum Tracked:
                </strong>

                ${data.maximum_tracked_persons}

            </p>

        </div>


        <div class="panel">

            <h2>
                Timeline
            </h2>


            <div class="timeline">

                ${
                    data.timeline
                        .map(
                            item => `

                            <div
                                class="timeline-row"
                            >

                                <div>
                                    ${
                                        item.timestamp
                                        || "-"
                                    }
                                </div>


                                <div>

                                    Attentive:
                                    ${
                                        item.attentive
                                    }

                                    |

                                    Not Attentive:
                                    ${
                                        item.not_attentive
                                    }

                                    |

                                    Unknown:
                                    ${
                                        item.unknown
                                    }

                                </div>


                                <div>

                                    Tracked:
                                    ${
                                        item.tracked_persons
                                    }

                                </div>

                            </div>

                        `
                        )
                        .join("")
                }

            </div>

        </div>

    `;

}


document
    .getElementById(
        "sessionSelect"
    )
    .addEventListener(
        "change",
        function() {

            loadAnalytics(
                this.value
            );

        }
    );


loadSessions();

</script>

</body>

</html>
"""


class ClassroomDashboardHandler(
    BaseHTTPRequestHandler
):

    def send_json(
        self,
        data,
        status=200
    ):

        body = json.dumps(
            data,
            indent=2
        ).encode(
            "utf-8"
        )


        self.send_response(
            status
        )


        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )


        self.send_header(
            "Content-Length",
            str(len(body))
        )


        self.end_headers()


        self.wfile.write(
            body
        )


    def send_html(
        self,
        html,
        status=200
    ):

        body = html.encode(
            "utf-8"
        )


        self.send_response(
            status
        )


        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )


        self.send_header(
            "Content-Length",
            str(len(body))
        )


        self.end_headers()


        self.wfile.write(
            body
        )


    def do_GET(self):

        global SESSION_MANAGER
        global ALERT_MANAGER


        parsed_url = urlparse(
            self.path
        )


        path = parsed_url.path


        query = parse_qs(
            parsed_url.query
        )


        print(
            f"[GET] {self.path}"
        )



        if path == "/video":

            try:

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "multipart/x-mixed-replace; boundary=frame"
                )

                self.send_header(
                    "Cache-Control",
                    "no-cache, no-store, must-revalidate"
                )

                self.send_header(
                    "Pragma",
                    "no-cache"
                )

                self.send_header(
                    "Expires",
                    "0"
                )

                self.end_headers()

                while True:

                    frame = CAMERA_STREAM.get_jpeg()

                    if frame is None:

                        time.sleep(
                            0.05
                        )

                        continue

                    self.wfile.write(
                        b"--frame\r\n"
                    )

                    self.wfile.write(
                        b"Content-Type: image/jpeg\r\n"
                    )

                    self.wfile.write(
                        (
                            f"Content-Length: {len(frame)}\r\n\r\n"
                        ).encode(
                            "utf-8"
                        )
                    )

                    self.wfile.write(
                        frame
                    )

                    self.wfile.write(
                        b"\r\n"
                    )

                    self.wfile.flush()

                    time.sleep(
                        0.03
                    )

            except (
                BrokenPipeError,
                ConnectionResetError,
                ConnectionAbortedError,
                OSError
            ):

                pass

            return


        if path == "/":

            self.send_html(
                DASHBOARD_HTML
            )

            return


        if path == "/index.html":

            self.send_html(
                DASHBOARD_HTML
            )

            return


        if path == "/analytics":

            self.send_html(
                ANALYTICS_HTML
            )

            return


        if path == "/health":

            self.send_json({

                "status":
                    "ok",

                "dashboard":
                    "running",

                "port":
                    PORT

            })

            return


        if path == "/api/state":

            state = load_state()


            if SESSION_MANAGER is not None:

                SESSION_MANAGER.record_state(
                    state
                )


            generated_alerts = []

            if ALERT_MANAGER is not None:
                generated_alerts = ALERT_MANAGER.process_state(
                  state
                     )


            self.send_json(
                state
            )

            return


        if path == "/api/alerts":

            alerts = []

            statistics = {

                "total": 0,

                "active": 0,

                "acknowledged": 0,

                "cleared": 0

            }


            if ALERT_MANAGER is not None:

                alerts =    ALERT_MANAGER.get_alerts(
                        limit=50
                    )

                statistics =     ALERT_MANAGER.get_statistics()


            self.send_json({

                "success":
                    True,

                "alerts":
                    alerts,

                "statistics":
                    statistics

            })

            return


        if path == "/api/alerts/acknowledge":

            alert_id =    query.get(
                    "alert_id",
                    [None]
                )[0]


            result = None


            if (
                ALERT_MANAGER is not None
                and alert_id
            ):

                result =    ALERT_MANAGER.acknowledge_alert(
                        alert_id
                    )


            self.send_json({

                "success":
                    result is not None,

                "alert":
                    result

            })

            return


        if path == "/api/alerts/clear":

            alert_id =   query.get(
                    "alert_id",
                    [None]
                )[0]


            result = None


            if (
                ALERT_MANAGER is not None
                and alert_id
            ):

                result =   ALERT_MANAGER.clear_alert(
                        alert_id
                    )


            self.send_json({

                "success":
                    result is not None,

                "alert":
                    result

            })

            return


        if path == "/api/sessions":

            sessions =    list_sessions()


            self.send_json(
                sessions
            )

            return


        if path == "/api/session":

            session_id =    query.get(
                    "session_id",
                    [None]
                )[0]


            session =     load_session(
                    session_id
                )


            if session is None:

                self.send_json(
                    {
                        "error":
                            "Session not found"
                    },
                    404
                )

                return


            self.send_json(
                session
            )

            return


        if path == "/api/analytics":

            session_id =    query.get(
                    "session_id",
                    [None]
                )[0]


            session =   load_session(
                    session_id
                )


            if session is None:

                self.send_json(
                    {
                        "error":
                            "Session not found"
                    },
                    404
                )

                return


            analytics =  calculate_analytics(
                    session
                )


            self.send_json(
                analytics
            )

            return


        self.send_json(

            {
                "error":
                    "404 - Not Found",

                "path":
                    path
            },

            404

        )


    def log_message(
        self,
        format,
        *args
    ):

        print(
            "[HTTP]",
            format % args
        )


def main():

    global SESSION_MANAGER
    global ALERT_MANAGER


    os.makedirs(
        SESSIONS_DIR,
        exist_ok=True
    )


    SESSION_MANAGER =  ClassroomSessionManager(
            sessions_dir=SESSIONS_DIR
        )


    ALERT_MANAGER = ClassroomAlertManager()


    SESSION_MANAGER.start_session()


    server =ThreadingHTTPServer(
            (
                HOST,
                PORT
            ),
            ClassroomDashboardHandler
        )


    print()

    print(
        "=" * 65
    )

    print(
        "AI SMART CLASSROOM"
    )

    print(
        "STEP 10 - CLASSROOM DASHBOARD"
    )

    print(
        "STEP 11 - CLASSROOM SESSION MANAGER"
    )

    print(
        "STEP 12 - HISTORICAL ANALYTICS"
    )

    print(
        "STEP 14 - ALERTS & NOTIFICATIONS"
    )

    print(
        "=" * 65
    )

    print()

    print(
        f"Dashboard : http://{HOST}:{PORT}/"
    )

    print(
        f"Analytics : http://{HOST}:{PORT}/analytics"
    )

    print(
        f"Health    : http://{HOST}:{PORT}/health"
    )

    print(
        f"Alerts    : http://{HOST}:{PORT}/api/alerts"
    )

    print()

    print(
        f"Sessions  : {SESSIONS_DIR}"
    )

    print()

    print(
        "Keep this terminal running."
    )

    print(
        "Press Ctrl+C to stop the classroom session."
    )

    print(
        "=" * 65
    )

    print()


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print()

        print(
            "Stopping classroom dashboard..."
        )


    finally:

        server.server_close()


        if SESSION_MANAGER is not None:

            SESSION_MANAGER.stop_session()


        print(
            "Dashboard stopped."
        )


if __name__ == "__main__":

    main()