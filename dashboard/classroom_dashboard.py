import json
import os

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dashboard.session_manager import ClassroomSessionManager

# ============================================================
# CONFIGURATION
# ============================================================

HOST = "127.0.0.1"

PORT = 5000

STATE_FILE = os.path.join(
    os.path.dirname(__file__),
    "classroom_state.json"
)


# ============================================================
# DEFAULT STATE
# ============================================================

DEFAULT_STATE = {
    "timestamp": "Waiting for STEP 9...",
    "tracked_persons": 0,
    "present_students": 0,
    "students": []
}


# ============================================================
# READ CLASSROOM STATE
# ============================================================

def read_state():

    try:

        if not os.path.exists(
            STATE_FILE
        ):

            return DEFAULT_STATE

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

            return DEFAULT_STATE

        return data

    except Exception:

        return DEFAULT_STATE


# ============================================================
# DASHBOARD HTML
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
AI Smart Classroom - Dashboard
</title>


<style>

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

    height: 82px;

    display: flex;

    align-items: center;

    justify-content: space-between;

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

    display: flex;

    align-items: center;

    gap: 8px;

    color:
        #65ff8a;

    font-weight:
        600;

}


.live-dot {

    width: 10px;

    height: 10px;

    border-radius:
        50%;

    background:
        #35ff6d;

    box-shadow:
        0 0 12px #35ff6d;

}


/* =========================================================
   MAIN
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
   PAGE TITLE
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
   GRID
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
   STUDENT TABLE
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
   RIGHT SIDE
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
         STAT CARDS
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
             STUDENT MONITOR
             ============================================== -->

        <div class="panel">

            <div class="panel-header">

                <h2>
                    Live Student Monitoring
                </h2>

                <span
                    id="lastUpdate"
                    style="color:#7f8ca0;font-size:12px;"
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
             CLASSROOM ANALYTICS
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
                            style="color:#63ff88"
                            id="systemStatus"
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
                            style="color:#63ff88"
                            id="cameraStatus"
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


            </div>

        </div>


    </section>


    <div class="footer">

        AI Smart Classroom · STEP 10 ·
        Classroom Dashboard

    </div>


</main>


<script>


// ==========================================================
// FETCH LIVE CLASSROOM STATE
// ==========================================================

async function updateDashboard() {

    try {

        const response = await fetch(
            "/api/state?t=" + Date.now()
        );

        if (!response.ok) {

            throw new Error(
                "State request failed"
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


    } catch (error) {

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
        data.students || [];


    let attentive = 0;

    let notAttentive = 0;

    let unknown = 0;


    students.forEach(
        student => {

            if (
                student.attention ===
                "ATTENTIVE"
            ) {

                attentive++;

            }

            else if (
                student.attention ===
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
        data.tracked_persons ?? 0;


    document.getElementById(
        "presentStudents"
    ).textContent =
        data.present_students ?? 0;


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
                (attentive / total) * 100
            );

        notAttentionRate =
            Math.round(
                (notAttentive / total) * 100
            );

        unknownRate =
            Math.round(
                (unknown / total) * 100
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


    document.getElementById(
        "systemStatus"
    ).textContent =
        total > 0
            ? "ACTIVE"
            : "WAITING";

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
        !students ||
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
                student.track_id ?? "--";


            const studentId =
                student.student_id
                || "UNKNOWN";


            const confidence =
                student.similarity != null
                    ? (
                        Number(
                            student.similarity
                        ) * 100
                    ).toFixed(1) + "%"
                    : "--";


            const attention =
                student.attention
                || "UNKNOWN";


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


            row.innerHTML = `

                <td>
                    #${track}
                </td>

                <td>
                    <strong>
                        ${studentId}
                    </strong>
                </td>

                <td>
                    ${confidence}
                </td>

                <td>

                    <span
                        class="status
                        ${statusClass}"
                    >

                        <span
                            class="status-dot"
                        ></span>

                        ${attention}

                    </span>

                </td>

            `;


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

    document.getElementById(
        "lastUpdate"
    ).textContent =
        timestamp || "--";


    document.getElementById(
        "dashboardTime"
    ).textContent =
        timestamp || "--";


    document.getElementById(
        "systemStatus"
    ).textContent =
        "ACTIVE";

}


// ==========================================================
// START LIVE UPDATES
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
# STEP 11 - GLOBAL SESSION MANAGER
# ============================================================

SESSION_MANAGER = None


# ============================================================
# HTTP SERVER
# ============================================================

class DashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # ----------------------------------------------------
        # API: LIVE CLASSROOM STATE
        # ----------------------------------------------------

        if path == "/api/state":

            state = read_state()

            # STEP 11:
            # Record the current classroom state in the
            # active classroom session, if a session exists.
            if SESSION_MANAGER is not None:

                try:

                    SESSION_MANAGER.record_state(state)

                except Exception as error:

                    # Do not allow session logging failure
                    # to break the live dashboard.
                    print(
                        f"Session record warning: {error}"
                    )

            response = json.dumps(
                state
            ).encode(
                "utf-8"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
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

        # ----------------------------------------------------
        # DASHBOARD PAGE
        # ----------------------------------------------------

        if path == "/" or path == "/index.html":

            response = HTML.encode(
                "utf-8"
            )

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

        # ----------------------------------------------------
        # 404
        # ----------------------------------------------------

        response = json.dumps(
            {
                "error": "Not Found",
                "path": path
            }
        ).encode(
            "utf-8"
        )

        self.send_response(404)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.end_headers()

        self.wfile.write(response)

    def log_message(
        self,
        format,
        *args
    ):

        # Keep terminal clean.
        return


# ============================================================
# START SERVER
# ============================================================

def main():

    global SESSION_MANAGER

    print("=" * 60)
    print("AI SMART CLASSROOM")
    print("STEP 10 - CLASSROOM DASHBOARD")
    print("STEP 11 - CLASSROOM SESSION MANAGER")
    print("=" * 60)

    print()
    print("State file:")
    print(f"  {STATE_FILE}")

    print()
    print("Dashboard URL:")
    print(f"  http://{HOST}:{PORT}")

    print()
    print("Starting classroom session...")

    # ========================================================
    # STEP 11 - CREATE SESSION MANAGER
    # ========================================================

    session_manager = ClassroomSessionManager()

    try:

        session_manager.start_session()

        SESSION_MANAGER = session_manager

        print("Session Manager: ACTIVE")

        print()
        print("Waiting for STEP 9 live data...")
        print("Keep this terminal running.")
        print("=" * 60)

        server = ThreadingHTTPServer(
            (
                HOST,
                PORT
            ),
            DashboardHandler
        )

        try:

            server.serve_forever()

        except KeyboardInterrupt:

            print()
            print("Stopping classroom session...")

        finally:

            server.server_close()

    finally:

        # Always stop the active session cleanly.
        if SESSION_MANAGER is not None:

            try:

                SESSION_MANAGER.stop_session()

            except Exception as error:

                print(
                    f"Session stop warning: {error}"
                )

            finally:

                SESSION_MANAGER = None

        print("Dashboard stopped.")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
