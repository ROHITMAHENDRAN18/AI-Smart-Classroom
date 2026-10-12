# AI Smart Classroom Attention Monitoring

## Overview

AI Smart Classroom Attention Monitoring is a computer vision-based intelligent classroom monitoring system.

The system provides:

- Automatic Attendance
- Face Recognition
- Multi-person Tracking
- Head Pose Estimation
- Eye State Detection
- Sleep Detection
- Phone Detection
- Hand Raise Detection
- Student Attention Score
- Teacher Dashboard
- Analytics Reports

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
coordinates and detector confidence for the most recently processed frame.
Frame results and images are not persisted. The current API does not connect
face identity, attendance, attention scoring, alerts, or analytics to this
browser frame flow; a detected person must not be treated as a student or an
attention result.

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
API client and the configured `VITE_DEFAULT_CLASSROOM_ID`. Classroom session
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

---

## Project Status

Phase 0 – Project Setup