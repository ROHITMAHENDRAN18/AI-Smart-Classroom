# AI Smart Classroom Attention Monitoring System

**An AI-powered classroom monitoring platform for face-based student identification, attendance tracking, and attention-state analysis.**

## Overview

The **AI Smart Classroom Attention Monitoring System** is a computer vision–based application designed to support classroom monitoring through automated student identification, attendance management, and attention-state analysis.

The system integrates a React frontend, FastAPI backend, PostgreSQL database, and computer vision components to provide a centralized interface for monitoring classroom sessions and reviewing attendance and attention analytics.

It uses face enrollment and facial embeddings to identify registered students, while eye-state and head-pose signals help estimate observable attention states. A temporal validation mechanism helps reduce unstable classifications caused by individual frames.

> **Important:** Attention labels are estimates based on observable visual signals. They do not establish a student's actual mental state, understanding, or learning outcome.

## Key Features

- **Student Registration** — Manage student information through the application.
- **Face Enrollment** — Capture and store facial embeddings for registered students.
- **Face Recognition** — Match detected faces against enrolled student representations.
- **Attendance Management** — Record and review attendance associated with classroom sessions.
- **Live Classroom Monitoring** — View recognized students and their current monitoring information.
- **Attention-State Analysis** — Estimate observable states using eye-state and head-pose signals.
- **Temporal Validation** — Use multiple observations over time to reduce unstable classifications.
- **Analytics Dashboard** — Review attendance summaries and attention-state distributions.
- **Historical Session Analysis** — Examine persisted records from completed or previous sessions.
- **Unknown-State Handling** — Preserve insufficient or conflicting visual evidence as `UNKNOWN` rather than forcing a potentially incorrect classification.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Axios |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Computer Vision | OpenCV |
| Face Recognition | InsightFace |
| Face Analysis Model | `buffalo_l` |
| API Documentation | FastAPI / Swagger UI |
| Development Environment | Python virtual environment, Node.js and npm |

## System Architecture

```mermaid
flowchart TD
    A[Classroom Camera] --> B[Video Frame Processing]
    B --> C[Face Detection and Recognition]
    C --> D{Registered Student?}
    D -->|Yes| E[Student Identification]
    D -->|No| F[Unknown Identity]
    E --> G[Attention Signal Analysis]
    G --> H[Temporal Validation]
    H --> I[Attention-State Estimate]
    E --> J[Attendance and Session Management]
    I --> K[FastAPI Backend]
    J --> K
    K --> L[(PostgreSQL Database)]
    L --> M[React Dashboard]
    K --> M
    M --> N[Live Monitoring and Analytics]
```

## Attention-State Classification

The system uses available eye-state and head-pose information to estimate observable attention states.

| State | Description |
|---|---|
| `LISTENING` | Visual signals are consistent with open eyes and a forward-facing head pose. |
| `SLEEPING` | Sustained eye closure or a downward head pose meets the implemented validation conditions. |
| `LOOKING_AWAY` | A valid head pose indicates that the student is looking away from the expected forward direction. |
| `UNKNOWN` | Evidence is insufficient, unavailable, or conflicting for a reliable state estimate. |

### Temporal Validation

Attention states are not determined solely from a single frame. The implemented validation process uses multiple valid observations over time before assigning a stable state.

This approach helps reduce short-lived classification changes caused by temporary detection errors or inconsistent visual signals.

**Limitations:**
- Camera position, lighting, occlusion, and face size can affect signal availability.
- Looking forward does not prove that a student is mentally attentive.
- Looking away does not necessarily mean that a student is distracted.
- The system does not infer talking from a single mouth-motion Boolean signal.
- `UNKNOWN` is a valid result and should not automatically be interpreted as inattentiveness.

## Project Modules

The application is organized into frontend, backend, database, and AI processing components.

```text
ai-smart-classroom/
├── ai/
│   ├── attendance/
│   ├── attention_engine/
│   ├── eye_detection/
│   ├── face_recognition/
│   ├── hand_detection/
│   ├── head_pose/
│   ├── person_detection/
│   ├── phone_detection/
│   ├── tracking/
│   └── utils/
├── backend/
│   ├── app/
│   ├── database/
│   ├── models/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── configs/
├── datasets/
├── embeddings/
├── frontend/
├── logs/
├── models/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

*Note: This is a representative project structure. Keep only directories and files that actually exist in the published repository.*

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.11
- Node.js and npm
- PostgreSQL
- Git
- A supported webcam or video input for camera-based monitoring

### 1. Clone the Repository

```bash
git clone https://github.com/ROHITMAHENDRAN18/ai-smart-classroom.git
cd ai-smart-classroom
```

Replace the repository URL if the project is published under a different GitHub repository name.

### 2. Set Up the Backend

Create and activate a Python virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the project's Python dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the repository uses a different dependency-management file, follow the instructions for that file instead.

### 3. Configure Environment Variables

Create a local environment file using the project's example:

```bash
cp .env.example .env
```

Configure the database connection and other required application settings in `.env`.

Example database URL format:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE_NAME
```

Use the actual database name, credentials, and driver configured by the project. Never commit passwords, API keys, or private environment files.

### 4. Initialize the Database

Make sure PostgreSQL is running and the configured database exists.

If the repository includes the table-creation script, run:

```bash
python -m scripts.create_tables
```

Use the project's actual database initialization or migration procedure if it differs.

### 5. Start the Backend

From the project root, run:

```bash
uvicorn backend.app.main:app --reload
```

The backend should be available at:

- Application: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

The exact endpoints depend on the routes enabled in the current version.

### 6. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, commonly:

`http://localhost:5173`

If the frontend uses an environment variable for its API base URL, configure it to point to the running backend.

## Application Workflow

1. Register student details.
2. Enroll a student's face using the supported capture workflow.
3. Start a classroom monitoring session.
4. Process camera frames and identify enrolled students.
5. Record eligible attendance and attention observations.
6. Review live monitoring information in the dashboard.
7. Examine attendance summaries and historical analytics.

Only verified, enrolled identities should be associated with student-specific records. An unknown face or an ordinary person detection must not be treated as proof of student identity.

## Database and Data Handling

PostgreSQL stores application records such as student information, classroom sessions, attendance, and supported monitoring history.

Facial embeddings are sensitive biometric data. Their collection and storage should be limited to authorized, consented use. Protect database access, restrict access to embedding files, and avoid publishing real student data or biometric information in the repository.

Historical analytics can only explain the information actually persisted by the application. If the database does not store the original eye-state and head-pose signals or diagnostic reasons, those details cannot reliably be reconstructed later.

## Testing and Validation

Run the project's available backend tests from the repository root:

```bash
pytest
```

Run frontend checks from the frontend directory using the scripts configured in `package.json`. Common commands include:

```bash
npm test
npm run build
```

These commands depend on the test runner and scripts included in the repository.

Before deployment, verify database connectivity, student enrollment, recognition behavior, session lifecycle, attendance persistence, attention-state handling, and dashboard analytics.

## Responsible Use and Limitations

This project is intended as a classroom monitoring and decision-support tool, not an automated authority for judging students.

- Obtain appropriate consent and institutional authorization before collecting classroom video or biometric data.
- Follow applicable privacy, data-protection, and educational policies.
- Restrict access to student records and stored facial embeddings.
- Provide human review for consequential attendance decisions.
- Do not equate visual attention estimates with learning, intelligence, or academic performance.
- Evaluate the system under varied classroom conditions before relying on its results.
- Do not publish confidential student data, camera recordings, credentials, or biometric embeddings.

## Future Enhancements

Potential areas for future development include:

- Improved robustness under varied lighting and camera angles.
- More comprehensive classroom session reporting.
- Enhanced student and teacher dashboards.
- Configurable monitoring and data-retention policies.
- Better tracking of signal quality and classification uncertainty.
- Evaluation of recognition and attention-state performance on appropriately consented datasets.
- Deployment and scalability improvements.

These items are possible extensions, not claims that every feature has already been implemented.

## Author

**Rohit M**  
B.Tech. — Artificial Intelligence and Data Science  
KPR Institute of Engineering and Technology  
Arasur, Coimbatore, Tamil Nadu, India

- GitHub: [ROHITMAHENDRAN18](https://github.com/ROHITMAHENDRAN18)
- Portfolio: [rohitmahendran18.github.io/portfolio](https://rohitmahendran18.github.io/portfolio/)

## License

Choose and add a license that matches how you intend to distribute this project. Until a license is added to the repository, reuse and redistribution permissions may be limited.

---

*Built as an applied AI and computer vision project exploring student identification, attendance management, and visual attention-state analysis in classroom environments.*
