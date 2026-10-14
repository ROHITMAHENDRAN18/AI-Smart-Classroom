# AI Smart Classroom Attention Monitoring

## Overview

AI Smart Classroom Attention Monitoring is a computer vision-based intelligent classroom monitoring system.

The repository contains experimental and legacy modules for several vision
tasks. The authenticated browser monitoring flow provides live YOLO person
detection, session-scoped IoU track IDs, OpenCV Haar face boxes when the
compatible OpenCV runtime is installed, persisted teacher-entered attendance,
and API-backed classroom reporting. Tracking IDs are not student identities.
Student recognition, attention estimation, and AI attendance remain
unavailable in the live API.

---

## Technology Stack

- Python
- FastAPI
- React
- PostgreSQL
- OpenCV
- YOLO
- MediaPipe
- InsightFace
- ByteTrack

## Live Monitoring Frame Processing

The authenticated Live Monitoring page can send resized JPEG camera frames to
the backend while an authorized classroom session is active. The backend uses
the configured YOLO model for person detection and returns real bounding-box
coordinates and detector confidence for the most recently processed frame. The
latest person and face boxes and frame metadata are saved in one bounded
summary row per session; raw images and face crops are not persisted. Face
detection uses the repository Haar cascade and reports no calibrated
confidence. It requires OpenCV 4.11 (`requirements.txt`); OpenCV 5 removed the
legacy cascade API, and the service reports face detection as an error when it
cannot process a frame. The session-local IoU tracker tolerates brief misses,
but is not ByteTrack and may switch IDs during crossings or large motion.
Student identity recognition, attention scoring, AI attendance, alerts, and
analytics are not connected to browser frame processing. A detected person,
face, or track must not be treated as a student or an attention result.

## Local startup

Configure the backend environment with `DATABASE_URL` and `JWT_SECRET_KEY`,
start PostgreSQL, then run `uvicorn backend.app.main:app --reload` from the
project root. In another terminal, set `VITE_DEFAULT_CLASSROOM_ID` in
`frontend/.env` to a classroom owned by the logged-in teacher and run
`npm run dev` from `frontend/`. Install backend dependencies from the root
`requirements.txt` and frontend dependencies with `npm install` first.

Set `YOLO_MODEL` in the backend environment to an available Ultralytics model
path. The default is `yolov8m.pt`, which is included in this repository.
The frame service checks that the configured weight file exists before model
initialization and does not download a replacement when it is missing.
Install backend dependencies from the root `requirements.txt`. The frame API
accepts authenticated `image/jpeg` uploads at
`POST /api/v1/classrooms/{classroom_id}/sessions/{session_id}/frames` for active
teacher-owned sessions. It returns person-class bounding boxes, detector
confidence, frame and processing timestamps, measured inference latency, and
per-feature connection status. It validates decoded image dimensions and
rate-limits each user/session within a backend process. Backend settings use
safe defaults and can be configured with
`FRAME_MAX_PAYLOAD_BYTES` (2 MiB; 1 KiB–10 MiB),
`FRAME_MAX_WIDTH` and `FRAME_MAX_HEIGHT` (1920; each 320–4096),
`FRAME_MAX_PIXELS` (2,073,600; 102,400–16,777,216),
`FRAME_MIN_INTERVAL_SECONDS` (1.5; 0.25–60), and
`FRAME_INFERENCE_TIMEOUT_SECONDS` (30; 1–300). Multi-worker deployments need
a shared rate-limit store to enforce the limit across workers.
Authorized teachers can reload the latest persisted result with
`GET /api/v1/classrooms/{classroom_id}/sessions/{session_id}/frame-summary`.

Frontend frame capture can be tuned with these non-secret Vite settings:

- `VITE_FRAME_CAPTURE_INTERVAL_MS` (default `2500`, minimum `2000`)
- `VITE_FRAME_CAPTURE_MAX_EDGE` (default `960`, maximum `1280`)
- `VITE_FRAME_JPEG_QUALITY` (default `0.75`, range `0.5`–`0.9`)
- `VITE_DETECTION_GRACE_PERIOD_MS` (default `6000` at the default 2500 ms
  capture interval; range `1000`–`30000`); real person boxes persist briefly
  across missed samples, then expire. By default this spans one missed sample
  and the following result with a small buffer.

Camera permission is requested only after the user enables the camera. HTTPS
or localhost is generally required by the browser. During an active monitoring
session, camera frames are transmitted to the configured backend for detection;
the live video preview itself remains in the browser.

## Classroom data pages

Dashboard, Students, Attendance, Analytics, and Reports use the authenticated
API client and `VITE_DEFAULT_CLASSROOM_ID`, which must be set in
`frontend/.env` to a positive classroom ID owned by the logged-in teacher
(discoverable through authenticated `GET /api/v1/classrooms`). Use only a
classroom returned for the logged-in account and restart Vite after changing
the value. Classroom session
history and student records are scoped to the authorized classroom. Attendance
history is served by
`GET /api/v1/classrooms/{classroom_id}/attendance`, which supports UTC `date`
or inclusive `from_date`/`to_date` filters and bounded `limit`/`offset`
pagination. Its summary counts cover the full filtered dataset, independent of
the current page. The attendance rate is present divided by known present plus
absent records; it is unavailable when that denominator is zero. Person
detections are not converted to student attendance. Reports display records
for a selected session; a report file export endpoint is not currently
implemented.

For an existing PostgreSQL database, run
`python -m scripts.migrations.migrate_frame_inference_summaries` and
`python -m scripts.migrations.migrate_attendance_session_student_unique`.
The attendance migration lists duplicate `(session_id, student_id)` keys and
stops without deleting records; review and resolve those records before
rerunning it. New databases receive both schema changes through SQLAlchemy
table creation.

---

## Project Status

Phase 0 – Project Setup
