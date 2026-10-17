# Debugging audit and implementation checklist

## Root causes verified

- The reported summary write failure was confirmed in `logs/app.log`: PostgreSQL raised `psycopg2.errors.UndefinedTable` for `frame_inference_summaries` when the service queried it. A read-only connection check identified the configured local database as `ai_smart_classroom`; its classrooms, sessions, attendance, and attention tables existed, but the summary table did not. This was an unapplied additive migration, not a YOLO or JSON serialization failure.
- `GET /api/v1/classrooms/{id}/sessions/active` is registered and authenticated. It returns HTTP 404 with the exact detail `No active classroom session` when the classroom is accessible but has no active session. The frontend must recognize that exact response only; other 404s are errors.
- The frame endpoint authenticates the teacher, checks classroom ownership and active session, bounds JPEG input, rate limits requests, and returns clipped pixel-coordinate YOLO boxes. It now persists the latest boxes and frame metadata in one bounded summary row per session; raw images are not stored. A persistence failure is reported separately from inference success.
- Attendance and attention tables are separate from the frontend frame path. Person boxes are not linked to students. The separate legacy face/tracking/attention code is not an integrated browser-frame pipeline.
- Manual attendance upsert functionality was already being added in the working tree. The schema had no database uniqueness guarantee for `(session_id, student_id)`, so concurrent writers could still create duplicates.
- Manual attendance writes are classroom/session authorized, committed transactionally, protected by a unique `(session_id, student_id)` constraint, and broadcast to refresh dashboard/data pages. This pass adds `attendance_source=MANUAL` for teacher writes; historical rows remain NULL because their provenance cannot be proven. The additive `migrate_attendance_source` migration was applied to the confirmed development database.
- Classroom/session data routes use teacher ownership checks. The frontend has a configurable classroom ID and authenticated API client, but the selected ID must exist in `/api/v1/classrooms` for the current teacher.
- The Students page previously listed records only. It now creates and enrolls students transactionally, edits student fields, and deactivates/reactivates classroom membership through teacher-scoped APIs.
- The legacy face and tracking pipeline was a standalone camera application. InsightFace and Supervision/ByteTrack are not declared runtime dependencies, the pickle embeddings have no classroom scope or consent metadata, and the student dataset's consent provenance is unknown. Its attention heuristic is not validated and none of these modules were connected to the authenticated frame endpoint.
- The actual `face_detection_failed` traceback in `logs/app.log` showed OpenCV 4.11 failing to parse `models/haarcascade/haarcascade_frontalface_default.xml`; inspection confirmed that file is zero bytes. The installed OpenCV package includes a valid frontal-face cascade. The frame service now uses that bundled cascade when the repository copy is missing or empty, and has a regression test for this failure. The earlier OpenCV 5 environment observation is stale; the active virtualenv now reports OpenCV 4.11.0.
- Recent classroom data failures had two causes: the configured `VITE_DEFAULT_CLASSROOM_ID=2` did not exist in the configured database (the authorized teacher owns classroom 1), and the model/API expected `attendance_source` before its migration existed. The local frontend setting now selects classroom 1, and the additive migration is applied.
- The browser frame route now returns independent Haar face boxes and an in-process session-scoped IoU tracker with monotonic IDs and short miss tolerance. Face boxes, detector status, and tracked person boxes are stored in the bounded summary. This tracker is not ByteTrack, and its IDs are not student identities.

## Checklist

- [x] Inspect API, auth, ORM models, existing schema scripts, frame pipeline, frontend API client and page changes.
- [x] Preserve the pre-existing working-tree changes.
- [x] Persist an image-free, bounded per-session detection summary and report persistence independently from inference.
- [x] Keep empty active-session handling exact and distinguish it from other HTTP failures.
- [x] Add database-level attendance uniqueness with a migration that refuses to discard duplicate history.
- [x] Run backend and frontend automated checks; report unavailable environment dependencies distinctly.
- [x] Verify the PostgreSQL schema and apply additive migrations to the confirmed local development database.
- [ ] Verify the browser end-to-end flow where camera/login are available.
- [x] Connect session-scoped person tracking and report its actual IDs; retain identity, attention, and AI attendance as unavailable.
- [x] Fall back to the installed OpenCV frontal-face cascade when the repository cascade is missing or empty, with tests for real cascade initialization and no-face inference.
- [x] Add persisted student create/enroll, edit, and classroom membership controls.

## Verification performed

- Latest verification: `.venv/bin/python -m pytest -q`: 116 passed. The added cascade test initializes the installed OpenCV cascade and processes a blank frame with zero face results.
- From `frontend/`, `npm run test:monitoring`: 13 passed; `npm run build`: succeeded; `npm run lint`: succeeded with warnings for pre-existing empty source files.
- Python bytecode compilation for the changed backend and migration files and `git diff --check` succeeded.
- PostgreSQL verification confirmed the `ai_smart_classroom` database and applied the attendance-source migration without updating historical records. Read-only FastAPI ASGI requests with test-injected teacher auth and the real database returned HTTP 200 for classroom overview, students, sessions, attendance, classroom analytics, and session report. The configured classroom currently has zero persisted attendance and attention records, so rates and report counts are empty/zero.
- Both migrations were rerun after schema validation was added; they reported no changes, confirming idempotence.
- The frame-summary migration added `face_detections` and `face_detection_status` to the configured local development database. Backend tests use SQLite; the live camera path was not exercised.
- Current `.venv` uses OpenCV 4.11.0. The actual logged face error was XML parsing failure because the tracked project cascade is empty (0 bytes).
- No consent-verified sample was used to claim that the cascade detects an actual person's face.
- Browser end-to-end verification was not run; no logged-in browser/camera session was available.

## Capability boundary

No raw classroom images or face crops are persisted. Track IDs are temporal IoU associations, not student identities. Safe recognition requires a consent workflow, a classroom-scoped protected embedding store, a compatible face model, and representative validation; these are absent. Attention remains unavailable because the existing heuristic is not validated for this use. AI attendance remains unavailable; manual attendance is preserved. Browser/camera end-to-end verification was not possible.
