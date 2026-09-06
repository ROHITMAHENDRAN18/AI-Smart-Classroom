import cv2
import numpy as np

from ultralytics import YOLO
import supervision as sv

from insightface.app import FaceAnalysis

from ai.face_recognition.face_track_association import (
    FaceTrackAssociator
)


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolov8m.pt"

EMBEDDINGS_FILE = "embeddings/face_embeddings.pkl"

SIMILARITY_THRESHOLD = 0.45


# ============================================================
# LOAD YOLO
# ============================================================

print("=" * 70)
print("Loading YOLOv8...")
print("=" * 70)

yolo_model = YOLO(YOLO_MODEL)

print("YOLOv8 Loaded Successfully.")


# ============================================================
# LOAD BYTE TRACK
# ============================================================

print("=" * 70)
print("Loading ByteTrack...")
print("=" * 70)

tracker = sv.ByteTrack()

print("ByteTrack Loaded Successfully.")


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print("=" * 70)
print("Loading InsightFace...")
print("=" * 70)

face_model = FaceAnalysis(
    name="buffalo_l"
)

face_model.prepare(
    ctx_id=-1,
    det_size=(640, 640)
)

print("InsightFace Loaded Successfully.")


# ============================================================
# LOAD FACE-TRACK ASSOCIATOR
# ============================================================

associator = FaceTrackAssociator(
    embeddings_file=EMBEDDINGS_FILE,
    similarity_threshold=SIMILARITY_THRESHOLD
)


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(0)

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)


if not camera.isOpened():

    print("ERROR: Cannot open camera.")

    exit()


print("=" * 70)
print("FACE + TRACK ASSOCIATION STARTED")
print("Press Q to exit")
print("=" * 70)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print("Failed to read camera frame.")

        break


    # ========================================================
    # STEP 1 — PERSON DETECTION
    # ========================================================

    results = yolo_model(
        frame,
        classes=[0],
        conf=0.35,
        iou=0.50,
        imgsz=960,
        max_det=100,
        verbose=False
    )[0]


    # ========================================================
    # STEP 2 — CONVERT YOLO → SUPERVISION
    # ========================================================

    detections = sv.Detections.from_ultralytics(
        results
    )


    # ========================================================
    # STEP 3 — PERSON CLASS ONLY
    # ========================================================

    if len(detections) > 0:

        detections = detections[
            detections.class_id == 0
        ]


    # ========================================================
    # STEP 4 — BYTE TRACK
    # ========================================================

    detections = tracker.update_with_detections(
        detections
    )


    # ========================================================
    # STEP 5 — FACE DETECTION
    # ========================================================

    faces = face_model.get(frame)


    # ========================================================
    # STEP 6 — STORE ASSOCIATIONS
    # ========================================================

    track_identity = {}


    # ========================================================
    # STEP 7 — MATCH EACH FACE WITH TRACK
    # ========================================================

    for face in faces:

        # ----------------------------------------------------
        # Face bounding box
        # ----------------------------------------------------

        fx1, fy1, fx2, fy2 = map(
            int,
            face.bbox
        )


        # ----------------------------------------------------
        # Face center
        # ----------------------------------------------------

        face_center_x = (
            fx1 + fx2
        ) // 2

        face_center_y = (
            fy1 + fy2
        ) // 2


        # ----------------------------------------------------
        # Face embedding
        # ----------------------------------------------------

        face_embedding = face.embedding

        if face_embedding is None:

            continue


        # ====================================================
        # FIND WHICH TRACK CONTAINS THE FACE
        # ====================================================

        matched_track_id = None

        for index, xyxy in enumerate(
            detections.xyxy
        ):

            x1, y1, x2, y2 = map(
                int,
                xyxy
            )


            # ------------------------------------------------
            # Check whether face center is inside person box
            # ------------------------------------------------

            if (
                x1 <= face_center_x <= x2
                and
                y1 <= face_center_y <= y2
            ):

                if detections.tracker_id is not None:

                    matched_track_id = int(
                        detections.tracker_id[index]
                    )

                break


        # ----------------------------------------------------
        # No matching person track
        # ----------------------------------------------------

        if matched_track_id is None:

            continue


        # ====================================================
        # IDENTIFY STUDENT
        # ====================================================

        student_id, similarity = associator.identify_face(
            face_embedding
        )


        # ====================================================
        # SAVE TRACK → STUDENT ASSOCIATION
        # ====================================================

        if student_id is not None:

            track_identity[
                matched_track_id
            ] = (
                student_id,
                similarity
            )


        # ====================================================
        # DRAW FACE BOX
        # ====================================================

        cv2.rectangle(
            frame,
            (fx1, fy1),
            (fx2, fy2),
            (255, 0, 0),
            2
        )


    # ========================================================
    # STEP 8 — DRAW PERSON TRACKS
    # ========================================================

    for index, xyxy in enumerate(
        detections.xyxy
    ):

        x1, y1, x2, y2 = map(
            int,
            xyxy
        )


        # ----------------------------------------------------
        # Track ID
        # ----------------------------------------------------

        if detections.tracker_id is not None:

            track_id = int(
                detections.tracker_id[index]
            )

        else:

            track_id = -1


        # ====================================================
        # CHECK IDENTITY
        # ====================================================

        if track_id in track_identity:

            student_id, similarity = (
                track_identity[track_id]
            )

            label = (
                f"{student_id} "
                f"ID:{track_id} "
                f"{similarity:.2f}"
            )

        else:

            label = (
                f"Unknown "
                f"ID:{track_id}"
            )


        # ====================================================
        # DRAW PERSON BOX
        # ====================================================

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )


        # ====================================================
        # DRAW LABEL
        # ====================================================

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


    # ========================================================
    # COUNT TRACKED PERSONS
    # ========================================================

    tracked_count = len(
        detections
    )


    cv2.putText(
        frame,
        f"Tracked Persons: {tracked_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "AI Smart Classroom - Face + Track Association",
        frame
    )


    # ========================================================
    # EXIT
    # ========================================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()

print("=" * 70)
print("Face + Track Association Stopped.")
print("=" * 70)