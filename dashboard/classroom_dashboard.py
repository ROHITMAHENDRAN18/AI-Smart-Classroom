import json
import os

from datetime import datetime

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer
)

from urllib.parse import (
    urlparse
)

from dashboard.session_manager import (
    ClassroomSessionManager
)


# ============================================================
# CONFIGURATION
# ============================================================

HOST = "127.0.0.1"

# IMPORTANT:
# Port 5000 may already be used by macOS Control Center.
# Therefore Step 12 uses 5050.
PORT = 5050


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


STATE_FILE = os.path.join(
    BASE_DIR,
    "classroom_state.json"
)


SESSIONS_DIR = os.path.join(
    BASE_DIR,
    "sessions"
)


# ============================================================
# DEFAULT STATE
# ============================================================

DEFAULT_STATE = {

    "timestamp":
        "Waiting for STEP 9...",

    "tracked_persons":
        0,

    "present_students":
        0,

    "students":
        []

}


# ============================================================
# READ CLASSROOM STATE
# ============================================================

def read_state():

    try:

        if not os.path.exists(
            STATE_FILE
        ):

            return DEFAULT_STATE.copy()


        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        if not isinstance(
            data,
            dict
        ):

            return DEFAULT_STATE.copy()


        # ----------------------------------------------------
        # Make sure required fields exist.
        # ----------------------------------------------------

        state = DEFAULT_STATE.copy()

        state.update(
            data
        )


        if not isinstance(
            state.get("students"),
            list
        ):

            state["students"] = []


        return state


    except Exception as error:

        print(
            f"[DASHBOARD] State read error: {error}"
        )

        return DEFAULT_STATE.copy()


# ============================================================
# HTML DASHBOARD
# ============================================================

HTML = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
AI Smart Classroom
</title>


<style>

/* =========================================================
   GLOBAL
   ========================================================= */

* {

    box-sizing: border-box;

    margin: 0;

    padding: 0;

}


body {

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    background:
        #070b12;

    color:
        #ffffff;

    min-height:
        100vh;

}


/* =========================================================
   HEADER
   ========================================================= */

.header {

    height:
        82px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    padding:
        0 32px;

    background:
        #0d131d;

    border-bottom:
        1px solid #253143;

}


.logo {

    font-size:
        24px;

    font-weight:
        700;

    letter-spacing:
        0.5px;

}


.logo span {

    color:
        #00e5ff;

}


.live {

    display:
        flex;

    align-items:
        center;

    gap:
        8px;

    color:
        #65ff8a;

    font-weight:
        600;

}


.live-dot {

    width:
        10px;

    height:
        10px;

    border-radius:
        50%;

    background:
        #35ff6d;

    box-shadow:
        0 0 12px #35ff6d;

}


/* =========================================================
   MAIN CONTAINER
   ========================================================= */

.container {

    max-width:
        1400px;

    margin:
        auto;

    padding:
        30px;

}


/* =========================================================
   TITLE
   ========================================================= */

.page-title {

    margin-bottom:
        26px;

}


.page-title h1 {

    font-size:
        32px;

    margin-bottom:
        7px;

}


.page-title p {

    color:
        #8e9bad;

}


/* =========================================================
   STAT CARDS
   ========================================================= */

.stats {

    display:
        grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap:
        18px;

    margin-bottom:
        25px;

}


.card {

    background:
        #101722;

    border:
        1px solid #263244;

    border-radius:
        16px;

    padding:
        22px;

}


.card-title {

    color:
        #8e9bad;

    font-size:
        14px;

    margin-bottom:
        12px;

}


.card-value {

    font-size:
        34px;

    font-weight:
        700;

}


.card-sub {

    margin-top:
        8px;

    font-size:
        13px;

    color:
        #718096;

}


.tracked .card-value {

    color:
        #00e5ff;

}


.present .card-value {

    color:
        #63ff88;

}


.attentive .card-value {

    color:
        #64ff91;

}


.not-attentive .card-value {

    color:
        #ff5f67;

}


/* =========================================================
   DASHBOARD GRID
   ========================================================= */

.dashboard-grid {

    display:
        grid;

    grid-template-columns:
        1.6fr 1fr;

    gap:
        22px;

}


/* =========================================================
   PANEL
   ========================================================= */

.panel {

    background:
        #101722;

    border:
        1px solid #263244;

    border-radius:
        16px;

    overflow:
        hidden;

}


.panel-header {

    padding:
        20px 22px;

    border-bottom:
        1px solid #263244;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

}


.panel-header h2 {

    font-size:
        18px;

}


.panel-body {

    padding:
        20px;

}


/* =========================================================
   TABLE
   ========================================================= */

.table-wrapper {

    overflow-x:
        auto;

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

    padding:
        13px;

    font-size:
        12px;

    color:
        #8794a7;

    border-bottom:
        1px solid #263244;

}


td {

    padding:
        15px 13px;

    border-bottom:
        1px solid #1e2837;

    font-size:
        14px;

}


tr:last-child td {

    border-bottom:
        none;

}


/* =========================================================
   STATUS
   ========================================================= */

.status {

    display:
        inline-flex;

    align-items:
        center;

    gap:
        7px;

    padding:
        6px 10px;

    border-radius:
        8px;

    font-size:
        12px;

    font-weight:
        600;

}


.status-dot {

    width:
        7px;

    height:
        7px;

    border-radius:
        50%;

}


.attentive-status {

    color:
        #65ff8a;

    background:
        rgba(54, 255, 110, 0.1);

}


.attentive-status .status-dot {

    background:
        #35ff6d;

}


.not-status {

    color:
        #ff6b73;

    background:
        rgba(255, 70, 80, 0.1);

}


.not-status .status-dot {

    background:
        #ff4c58;

}


.unknown-status {

    color:
        #ffd45c;

    background:
        rgba(255, 190, 50, 0.1);

}


.unknown-status .status-dot {

    background:
        #ffc247;

}


/* =========================================================
   METRICS
   ========================================================= */

.metric {

    margin-bottom:
        25px;

}


.metric:last-child {

    margin-bottom:
        0;

}


.metric-top {

    display:
        flex;

    justify-content:
        space-between;

    margin-bottom:
        10px;

}


.metric-name {

    color:
        #aab5c5;

}


.metric-number {

    font-weight:
        700;

}


.progress {

    width:
        100%;

    height:
        10px;

    background:
        #202b3a;

    border-radius:
        10px;

    overflow:
        hidden;

}


.progress-bar {

    height:
        100%;

    width:
        0%;

    border-radius:
        10px;

    transition:
        width 0.4s ease;

}


.green {

    background:
        #38ff73;

}


.red {

    background:
        #ff4c58;

}


.yellow {

    background:
        #ffc247;

}


/* =========================================================
   CLASSROOM STATUS
   ========================================================= */

.classroom-status {

    display:
        flex;

    flex-direction:
        column;

    gap:
        14px;

}


.status-row {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    padding:
        14px;

    background:
        #0c121b;

    border:
        1px solid #202b3a;

    border-radius:
        10px;

}


.status-label {

    color:
        #9aa7b8;

}


.status-value {

    font-weight:
        700;

}


/* =========================================================
   SESSION PANEL
   ========================================================= */

.session-box {

    margin-top:
        25px;

    padding:
        18px;

    background:
        #0c121b;

    border:
        1px solid #202b3a;

    border-radius:
        12px;

}


.session-title {

    font-size:
        14px;

    color:
        #8e9bad;

    margin-bottom:
        10px;

}


.session-id {

    font-size:
        15px;

    font-weight:
        700;

    color:
        #00e5ff;

    word-break:
        break-all;

}


/* =========================================================
   FOOTER
   ========================================================= */

.footer {

    margin-top:
        25px;

    padding:
        20px;

    text-align:
        center;

    color:
        #647184;

    font-size:
        13px;

}


/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (
    max-width: 1000px
) {

    .stats {

        grid-template-columns:
            repeat(2, 1fr);

    }


    .dashboard-grid {

        grid-template-columns:
            1fr;

    }

}


@media (
    max-width: 600px
) {

    .header {

        padding:
            0 16px;

    }


    .logo {

        font-size:
            18px;

    }


    .container {

        padding:
            18px;

    }


    .stats {

        grid-template-columns:
            1fr;

    }

}

</style>

</head>


<body>


<!-- ======================================================
     HEADER
     ====================================================== -->

<header class="header">

    <div class="logo">

        AI SMART <span>CLASSROOM</span>

    </div>


    <div class="live">

        <div class="live-dot"></div>

        LIVE

    </div>

</header>


<!-- ======================================================
     MAIN
     ====================================================== -->

<main class="container">


    <div class="page-title">

        <h1>
            Classroom Dashboard
        </h1>

        <p>
            Real-time student attendance and attention monitoring
        </p>

    </div>


    <!-- ==================================================
         STATISTICS
         ================================================== -->

    <section class="stats">


        <div class="card tracked">

            <div class="card-title">
                TRACKED PERSONS
            </div>

            <div
                class="card-value"
                id="trackedPersons"
            >
                0
            </div>

            <div class="card-sub">
                Currently detected
            </div>

        </div>


        <div class="card present">

            <div class="card-title">
                PRESENT STUDENTS
            </div>

            <div
                class="card-value"
                id="presentStudents"
            >
                0
            </div>

            <div class="card-sub">
                Recognized students
            </div>

        </div>


        <div class="card attentive">

            <div class="card-title">
                ATTENTIVE
            </div>

            <div
                class="card-value"
                id="attentiveStudents"
            >
                0
            </div>

            <div class="card-sub">
                Currently attentive
            </div>

        </div>


        <div class="card not-attentive">

            <div class="card-title">
                NOT ATTENTIVE
            </div>

            <div
                class="card-value"
                id="notAttentiveStudents"
            >
                0
            </div>

            <div class="card-sub">
                Need attention
            </div>

        </div>


    </section>


    <!-- ==================================================
         DASHBOARD GRID
         ================================================== -->

    <section class="dashboard-grid">


        <!-- ==============================================
             STUDENT MONITORING
             ============================================== -->

        <div class="panel">

            <div class="panel-header">

                <h2>
                    Live Student Monitoring
                </h2>

                <span
                    id="lastUpdate"
                    style="
                        color:#7f8ca0;
                        font-size:12px;
                    "
                >
                    Waiting...
                </span>

            </div>


            <div class="panel-body">

                <div class="table-wrapper">

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


                        <tbody id="studentTable">

                            <tr>

                                <td
                                    colspan="4"
                                    style="
                                        text-align:center;
                                        color:#718096;
                                        padding:30px;
                                    "
                                >

                                    Waiting for STEP 9...

                                </td>

                            </tr>

                        </tbody>

                    </table>

                </div>

            </div>

        </div>


        <!-- ==============================================
             ANALYTICS
             ============================================== -->

        <div class="panel">

            <div class="panel-header">

                <h2>
                    Classroom Analytics
                </h2>

            </div>


            <div class="panel-body">


                <div class="metric">

                    <div class="metric-top">

                        <span class="metric-name">
                            Attention Rate
                        </span>

                        <span
                            class="metric-number"
                            id="attentionRate"
                        >
                            0%
                        </span>

                    </div>


                    <div class="progress">

                        <div
                            id="attentionBar"
                            class="progress-bar green"
                        ></div>

                    </div>

                </div>


                <div class="metric">

                    <div class="metric-top">

                        <span class="metric-name">
                            Not Attention Rate
                        </span>

                        <span
                            class="metric-number"
                            id="notAttentionRate"
                        >
                            0%
                        </span>

                    </div>


                    <div class="progress">

                        <div
                            id="notAttentionBar"
                            class="progress-bar red"
                        ></div>

                    </div>

                </div>


                <div class="metric">

                    <div class="metric-top">

                        <span class="metric-name">
                            Unknown / Processing
                        </span>

                        <span
                            class="metric-number"
                            id="unknownRate"
                        >
                            0%
                        </span>

                    </div>


                    <div class="progress">

                        <div
                            id="unknownBar"
                            class="progress-bar yellow"
                        ></div>

                    </div>

                </div>


                <div
                    style="
                        height:1px;
                        background:#263244;
                        margin:25px 0;
                    "
                ></div>


                <div class="classroom-status">


                    <div class="status-row">

                        <span class="status-label">
                            System
                        </span>

                        <span
                            class="status-value"
                            id="systemStatus"
                            style="color:#63ff88"
                        >
                            WAITING
                        </span>

                    </div>


                    <div class="status-row">

                        <span class="status-label">
                            Camera
                        </span>

                        <span
                            class="status-value"
                            id="cameraStatus"
                            style="color:#63ff88"
                        >
                            MONITORING
                        </span>

                    </div>


                    <div class="status-row">

                        <span class="status-label">
                            Last Update
                        </span>

                        <span
                            class="status-value"
                            id="dashboardTime"
                        >
                            --
                        </span>

                    </div>


                </div>


                <!-- ======================================
                     SESSION INFORMATION
                     ====================================== -->

                <div class="session-box">

                    <div class="session-title">
                        CLASSROOM SESSION
                    </div>

                    <div
                        class="session-id"
                        id="sessionId"
                    >
                        Waiting...
                    </div>

                </div>


            </div>

        </div>


    </section>


    <div class="footer">

        AI Smart Classroom ·
        STEP 10 Dashboard ·
        STEP 11 Session Manager ·
        STEP 12 Analytics Ready

    </div>


</main>


<script>


// ==========================================================
// FETCH LIVE CLASSROOM STATE
// ==========================================================

async function updateDashboard() {

    try {

        const response =
            await fetch(
                "/api/state?t=" +
                Date.now()
            );


        if (!response.ok) {

            throw new Error(
                "State request failed: " +
                response.status
            );

        }


        const data =
            await response.json();


        updateStatistics(
            data
        );


        updateStudentTable(
            data.students || []
        );


        updateTime(
            data.timestamp
        );


        updateSessionInfo(
            data
        );


        document.getElementById(
            "systemStatus"
        ).textContent =
            "ACTIVE";


    }

    catch (error) {

        console.log(
            "Dashboard update error:",
            error
        );


        document.getElementById(
            "systemStatus"
        ).textContent =
            "OFFLINE";

    }

}


// ==========================================================
// UPDATE STATISTICS
// ==========================================================

function updateStatistics(
    data
) {

    const students =
        Array.isArray(
            data.students
        )
            ? data.students
            : [];


    let attentive = 0;

    let notAttentive = 0;

    let unknown = 0;


    students.forEach(
        student => {

            const attention =
                student.attention ||
                "UNKNOWN";


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


    const total =
        students.length;


    document.getElementById(
        "trackedPersons"
    ).textContent =
        Number(
            data.tracked_persons || 0
        );


    document.getElementById(
        "presentStudents"
    ).textContent =
        Number(
            data.present_students || 0
        );


    document.getElementById(
        "attentiveStudents"
    ).textContent =
        attentive;


    document.getElementById(
        "notAttentiveStudents"
    ).textContent =
        notAttentive;


    let attentionRate = 0;

    let notAttentionRate = 0;

    let unknownRate = 0;


    if (total > 0) {

        attentionRate =
            Math.round(
                (
                    attentive /
                    total
                ) * 100
            );


        notAttentionRate =
            Math.round(
                (
                    notAttentive /
                    total
                ) * 100
            );


        unknownRate =
            Math.round(
                (
                    unknown /
                    total
                ) * 100
            );

    }


    document.getElementById(
        "attentionRate"
    ).textContent =
        attentionRate + "%";


    document.getElementById(
        "notAttentionRate"
    ).textContent =
        notAttentionRate + "%";


    document.getElementById(
        "unknownRate"
    ).textContent =
        unknownRate + "%";


    document.getElementById(
        "attentionBar"
    ).style.width =
        attentionRate + "%";


    document.getElementById(
        "notAttentionBar"
    ).style.width =
        notAttentionRate + "%";


    document.getElementById(
        "unknownBar"
    ).style.width =
        unknownRate + "%";

}


// ==========================================================
// UPDATE STUDENT TABLE
// ==========================================================

function updateStudentTable(
    students
) {

    const table =
        document.getElementById(
            "studentTable"
        );


    if (
        !Array.isArray(
            students
        )
        ||
        students.length === 0
    ) {

        table.innerHTML = `

            <tr>

                <td
                    colspan="4"
                    style="
                        text-align:center;
                        color:#718096;
                        padding:30px;
                    "
                >

                    No students detected

                </td>

            </tr>

        `;

        return;

    }


    table.innerHTML = "";


    students.forEach(
        student => {

            const row =
                document.createElement(
                    "tr"
                );


            const track =
                student.track_id ??
                "--";


            const studentId =
                student.student_id ||
                "UNKNOWN";


            const confidence =
                student.similarity != null
                    ? (
                        Number(
                            student.similarity
                        ) * 100
                    ).toFixed(1) + "%"
                    : "--";


            const attention =
                student.attention ||
                "UNKNOWN";


            let statusClass =
                "unknown-status";


            if (
                attention ===
                "ATTENTIVE"
            ) {

                statusClass =
                    "attentive-status";

            }

            else if (
                attention ===
                "NOT ATTENTIVE"
            ) {

                statusClass =
                    "not-status";

            }


            // ------------------------------------------------
            // Use textContent instead of directly inserting
            // untrusted student values into HTML.
            // ------------------------------------------------

            const trackCell =
                document.createElement(
                    "td"
                );


            trackCell.textContent =
                "#" + track;


            const studentCell =
                document.createElement(
                    "td"
                );


            const strong =
                document.createElement(
                    "strong"
                );


            strong.textContent =
                studentId;


            studentCell.appendChild(
                strong
            );


            const confidenceCell =
                document.createElement(
                    "td"
                );


            confidenceCell.textContent =
                confidence;


            const attentionCell =
                document.createElement(
                    "td"
                );


            const status =
                document.createElement(
                    "span"
                );


            status.className =
                "status " +
                statusClass;


            const dot =
                document.createElement(
                    "span"
                );


            dot.className =
                "status-dot";


            status.appendChild(
                dot
            );


            status.appendChild(
                document.createTextNode(
                    attention
                )
            );


            attentionCell.appendChild(
                status
            );


            row.appendChild(
                trackCell
            );


            row.appendChild(
                studentCell
            );


            row.appendChild(
                confidenceCell
            );


            row.appendChild(
                attentionCell
            );


            table.appendChild(
                row
            );

        }
    );

}


// ==========================================================
// UPDATE TIME
// ==========================================================

function updateTime(
    timestamp
) {

    const value =
        timestamp || "--";


    document.getElementById(
        "lastUpdate"
    ).textContent =
        value;


    document.getElementById(
        "dashboardTime"
    ).textContent =
        value;

}


// ==========================================================
// UPDATE SESSION INFORMATION
// ==========================================================

function updateSessionInfo(
    data
) {

    const sessionId =
        data.session_id ||
        "SESSION ACTIVE";


    document.getElementById(
        "sessionId"
    ).textContent =
        sessionId;

}


// ==========================================================
// START DASHBOARD
// ==========================================================

updateDashboard();


setInterval(
    updateDashboard,
    1000
);


</script>


</body>

</html>
"""

# ============================================================
# HTTP REQUEST HANDLER
# ============================================================

class DashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        try:

            parsed_url = urlparse(self.path)

            path = parsed_url.path

            # ------------------------------------------------
            # API: CLASSROOM STATE
            # ------------------------------------------------

            if path == "/api/state":

                state = read_state()

                response = json.dumps(
                    state,
                    ensure_ascii=False
                ).encode("utf-8")

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
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

                self.send_header(
                    "Access-Control-Allow-Origin",
                    "*"
                )

                self.send_header(
                    "Content-Length",
                    str(len(response))
                )

                self.end_headers()

                self.wfile.write(response)

                return

            # ------------------------------------------------
            # API: SESSION STATUS
            # ------------------------------------------------

            if path == "/api/session":

                response_data = {
                    "status": "ACTIVE",
                    "dashboard": "ONLINE",
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    )
                }

                response = json.dumps(
                    response_data
                ).encode("utf-8")

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.send_header(
                    "Cache-Control",
                    "no-cache"
                )

                self.send_header(
                    "Content-Length",
                    str(len(response))
                )

                self.end_headers()

                self.wfile.write(response)

                return

            # ------------------------------------------------
            # DASHBOARD PAGE
            # ------------------------------------------------

            if (
                path == "/"
                or
                path == "/index.html"
            ):

                response = HTML.encode("utf-8")

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
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

                self.send_header(
                    "Content-Length",
                    str(len(response))
                )

                self.end_headers()

                self.wfile.write(response)

                return

            # ------------------------------------------------
            # 404
            # ------------------------------------------------

            response = b"404 - Not Found"

            self.send_response(404)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(response))
            )

            self.end_headers()

            self.wfile.write(response)

        except Exception as error:

            print(
                f"[HTTP] Request error: {error}"
            )

    def log_message(
        self,
        format,
        *args
    ):

        return


# ============================================================
# START SERVER
# ============================================================

def main():

    print("=" * 60)

    print("AI SMART CLASSROOM")

    print("STEP 10 - CLASSROOM DASHBOARD")

    print("STEP 11 - CLASSROOM SESSION MANAGER")

    print("STEP 12 - DASHBOARD SERVER FIX")

    print("=" * 60)

    print()

    print("State file:")

    print(f"  {STATE_FILE}")

    print()

    print("Sessions directory:")

    print(f"  {SESSIONS_DIR}")

    print()

    print("Dashboard URL:")

    print(f"  http://{HOST}:{PORT}")

    print()

    print("Starting classroom session...")

    # --------------------------------------------------------
    # SESSION MANAGER
    # --------------------------------------------------------

    session_manager = ClassroomSessionManager(
        sessions_dir=SESSIONS_DIR
    )

    session_id = session_manager.start_session()

    print(
        f"Session Manager: ACTIVE"
    )

    print(
        f"Session ID: {session_id}"
    )

    print()

    print(
        "Waiting for STEP 9 live data..."
    )

    print(
        "Keep this terminal running."
    )

    print("=" * 60)

    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    server = ThreadingHTTPServer(
        (HOST, PORT),
        DashboardHandler
    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print()

        print(
            "Stopping classroom session..."
        )

    finally:

        server.server_close()

        try:

            if session_manager.active:

                session_manager.stop_session()

        except Exception as error:

            print(
                f"[SESSION] Stop error: {error}"
            )

        print(
            "Dashboard stopped."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()