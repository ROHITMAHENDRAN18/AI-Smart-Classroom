# Debugging audit and implementation checklist

## Root causes verified

- The reported summary write failure was confirmed in `logs/app.log`: PostgreSQL raised `psycopg2.errors.UndefinedTable` for `frame_inference_summaries` when the service queried it. A read-only connection check identified the configured local database as `ai_smart_classroom`; its classrooms, sessions, attendance, and attention tables existed, but the summary table did not. This was an unapplied additive migration, not a YOLO or JSON serialization failure.
- `GET /api/v1/classrooms/{id}/sessions/active` is registered and authenticated. It returns HTTP 404 with the exact detail `No active classroom session` when the classroom is accessible but has no active session. The frontend must recognize that exact response only; other 404s are errors.
- The frame endpoint authenticates the teacher, checks classroom ownership and active session, bounds JPEG input, rate limits requests, and returns clipped pixel-coordinate YOLO boxes. It now persists the latest boxes and frame metadata in one bounded summary row per session; raw images are not stored. A persistence failure is reported separately from inference success.
- Attendance and attention tables are separate from the frontend frame path. Person boxes are not linked to students. The separate legacy face/tracking/attention code is not an integrated browser-frame pipeline.
- Manual attendance upsert functionality was already being added in the working tree. The schema had no database uniqueness guarantee for `(session_id, student_id)`, so concurrent writers could still create duplicates.
- Classroom/session data routes use teacher ownership checks. The frontend has a configurable classroom ID and authenticated API client, but the selected ID must exist in `/api/v1/classrooms` for the current teacher.
- The Students page previously listed records only. It now creates and enrolls students transactionally, edits student fields, and deactivates/reactivates classroom membership through teacher-scoped APIs.
- The legacy face and tracking pipeline was a standalone camera application. InsightFace and Supervision/ByteTrack are not declared runtime dependencies, the pickle embeddings have no classroom scope or consent metadata, and the student dataset's consent provenance is unknown. Its attention heuristic is not validated and none of these modules were connected to the authenticated frame endpoint.
- The active environment is Python 3.13 with OpenCV 5.0.0.93. That build no longer exposes `cv2.CascadeClassifier`, so the available Haar XML could not be used at runtime. Requirements now pin OpenCV 4.11.0.86; installation could not complete because package network access is unavailable in this environment. The API reports a per-frame face detector error until the pinned dependency is installed.
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
- [x] Connect face detection when the Haar runtime can process a frame; report an error when it cannot.
- [x] Add persisted student create/enroll, edit, and classroom membership controls.

## Verification performed

- `python -m pytest -q`: 114 passed after adding live tracker and face detector behavior tests.
- From `frontend/`, `npm run test:monitoring`: 13 passed; `npm run build`: succeeded; `npm run lint`: succeeded with warnings for pre-existing empty source files.
- Python bytecode compilation for the changed backend and migration files and `git diff --check` succeeded.
- PostgreSQL read-only verification confirmed the `ai_smart_classroom` database. Both migrations were applied successfully; a final read-only check confirmed the summary table and expected columns, the attendance uniqueness constraint, and zero duplicate attendance keys.
- Both migrations were rerun after schema validation was added; they reported no changes, confirming idempotence.
- The frame-summary migration added `face_detections` and `face_detection_status` to the configured local development database. Backend tests use SQLite; the live camera path was not exercised.
- OpenCV 4 installation was attempted but failed because network name resolution is unavailable. The current OpenCV 5 runtime was directly confirmed to lack `CascadeClassifier`; face detection therefore cannot be reported as connected on this machine yet.
- Browser end-to-end verification was not run; no logged-in browser/camera session was available.

## Capability boundary

No raw classroom images or face crops are persisted. Track IDs are temporal IoU associations, not student identities. Safe recognition requires a consent workflow, a classroom-scoped protected embedding store, a compatible face model, and representative validation; these are absent. Attention remains unavailable because the existing heuristic is not validated for this use. AI attendance remains unavailable; manual attendance is preserved. Browser/camera end-to-end verification was not possible.
