import cv2
import numpy as np
import pickle

from ultralytics import YOLO
import supervision as sv

from insightface.app import FaceAnalysis

from ai.attendance.attendance_manager import AttendanceManager


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolov8m.pt"

EMBEDDINGS_FILE = "embeddings/face_embeddings.pkl"

CAMERA_INDEX = 0

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

YOLO_CONFIDENCE = 0.35
YOLO_IOU = 0.50
YOLO_IMAGE_SIZE = 960

FACE_DETECTION_SIZE = (640, 640)

FACE_MATCH_THRESHOLD = 0.45


# ============================================================
# 1. LOAD YOLO PERSON DETECTOR
# ============================================================

print("=" * 70)
print("Loading YOLO Person Detector...")
print("=" * 70)

model = YOLO(
    YOLO_MODEL
)

print("YOLO Loaded Successfully.")


# ============================================================
# 2. LOAD BYTE TRACK
# ============================================================

print("=" * 70)
print("Loading ByteTrack...")
print("=" * 70)

tracker = sv.ByteTrack()

print("ByteTrack Loaded Successfully.")


# ============================================================
# 3. LOAD ATTENDANCE MANAGER
# ============================================================

print("=" * 70)
print("Loading Attendance Manager...")
print("=" * 70)

attendance_manager = AttendanceManager()

print("Attendance Manager Loaded Successfully.")


# ============================================================
# 4. LOAD INSIGHTFACE
# ============================================================

print("=" * 70)
print("Loading InsightFace...")
print("=" * 70)

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=[
        "CPUExecutionProvider"
    ]
)

face_app.prepare(
    ctx_id=0,
    det_size=FACE_DETECTION_SIZE
)

print("InsightFace Loaded Successfully.")


# ============================================================
# 5. LOAD FACE EMBEDDINGS
# ============================================================

print("=" * 70)
print("Loading Face Embeddings...")
print("=" * 70)

with open(
    EMBEDDINGS_FILE,
    "rb"
) as file:

    known_embeddings = pickle.load(
        file
    )


print("Known Students:")

for student_id, embeddings in known_embeddings.items():

    print(
        f"  - {student_id}: "
        f"{len(embeddings)} embeddings"
    )


# ============================================================
# 6. NORMALIZE EMBEDDING
# ============================================================

def normalize_embedding(
    embedding
):

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    )

    norm = np.linalg.norm(
        embedding
    )

    if norm == 0:

        return embedding

    return embedding / norm


# ============================================================
# 7. PREPARE KNOWN EMBEDDINGS
# ============================================================

def prepare_known_embeddings(
    embeddings_dict
):

    prepared = {}

    for student_id, embeddings in embeddings_dict.items():

        normalized_embeddings = []

        for embedding in embeddings:

            normalized = normalize_embedding(
                embedding
            )

            normalized_embeddings.append(
                normalized
            )

        if normalized_embeddings:

            prepared[student_id] = np.vstack(
                normalized_embeddings
            )

    return prepared


known_embeddings = prepare_known_embeddings(
    known_embeddings
)


# ============================================================
# 8. FACE RECOGNITION
# ============================================================

def recognize_face(
    face_embedding
):

    query_embedding = normalize_embedding(
        face_embedding
    )

    best_student_id = None

    best_score = -1.0

    for student_id, student_embeddings in known_embeddings.items():

        similarities = np.dot(
            student_embeddings,
            query_embedding
        )

        student_best_score = float(
            np.max(similarities)
        )

        if student_best_score > best_score:

            best_score = student_best_score

            best_student_id = student_id

    if best_score >= FACE_MATCH_THRESHOLD:

        return (
            best_student_id,
            best_score
        )

    return (
        None,
        best_score
    )


# ============================================================
# 9. FIND TRACK FOR FACE
# ============================================================

def find_track_for_face(
    face,
    detections
):

    bbox = face.bbox

    face_x1 = float(
        bbox[0]
    )

    face_y1 = float(
        bbox[1]
    )

    face_x2 = float(
        bbox[2]
    )

    face_y2 = float(
        bbox[3]
    )

    face_center_x = (
        face_x1 + face_x2
    ) / 2

    face_center_y = (
        face_y1 + face_y2
    ) / 2

    best_track_id = None

    best_distance = float(
        "inf"
    )

    for i in range(
        len(detections)
    ):

        x1, y1, x2, y2 = detections.xyxy[i]

        # ----------------------------------------------------
        # Face center must be inside person bounding box
        # ----------------------------------------------------

        inside_person = (
            x1 <= face_center_x <= x2
            and
            y1 <= face_center_y <= y2
        )

        if not inside_person:

            continue

        person_center_x = (
            x1 + x2
        ) / 2

        person_center_y = (
            y1 + y2
        ) / 2

        distance = np.sqrt(
            (
                face_center_x
                - person_center_x
            ) ** 2
            +
            (
                face_center_y
                - person_center_y
            ) ** 2
        )

        if distance < best_distance:

            best_distance = distance

            best_track_id = int(
                detections.tracker_id[i]
            )

    return best_track_id


# ============================================================
# 10. OPEN CAMERA
# ============================================================

print("=" * 70)
print("Opening Camera...")
print("=" * 70)

camera = cv2.VideoCapture(
    CAMERA_INDEX
)

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    FRAME_WIDTH
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    FRAME_HEIGHT
)


if not camera.isOpened():

    print(
        "ERROR: Cannot open camera."
    )

    raise SystemExit


# ============================================================
# 11. START STEP 7
# ============================================================

print("=" * 70)
print("AI SMART CLASSROOM")
print("STEP 7 - ATTENDANCE INTEGRATION")
print("=" * 70)

print(
    "Face + Person + Track + Attendance"
)

print("Press Q to exit.")

print("=" * 70)


# ============================================================
# 12. MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print(
            "ERROR: Failed to read camera frame."
        )

        break


    # ========================================================
    # PERSON DETECTION
    # ========================================================

    results = model(
        frame,
        classes=[0],
        conf=YOLO_CONFIDENCE,
        iou=YOLO_IOU,
        imgsz=YOLO_IMAGE_SIZE,
        max_det=100,
        verbose=False
    )[0]


    # ========================================================
    # YOLO → SUPERVISION
    # ========================================================

    detections = sv.Detections.from_ultralytics(
        results
    )


    # ========================================================
    # PERSON ONLY
    # ========================================================

    if len(detections) > 0:

        detections = detections[
            detections.class_id == 0
        ]


    # ========================================================
    # BYTE TRACK
    # ========================================================

    if len(detections) > 0:

        detections = tracker.update_with_detections(
            detections
        )


    # ========================================================
    # FACE DETECTION
    # ========================================================

    faces = face_app.get(
        frame
    )


    # ========================================================
    # TRACKED PERSON COUNT
    # ========================================================

    tracked_person_count = len(
        detections
    )


    cv2.putText(
        frame,
        f"Tracked Persons: {tracked_person_count}",
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        3
    )


    # ========================================================
    # ATTENDANCE COUNT
    # ========================================================

    attendance_count = (
        attendance_manager.get_present_count()
    )


    cv2.putText(
        frame,
        f"Present: {attendance_count}",
        (20, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        3
    )


    # ========================================================
    # PROCESS EVERY FACE
    # ========================================================

    for face in faces:

        if not hasattr(
            face,
            "embedding"
        ):

            continue


        # ====================================================
        # FACE RECOGNITION
        # ====================================================

        student_id, similarity = recognize_face(
            face.embedding
        )


        # ====================================================
        # FIND BYTE TRACK ID
        # ====================================================

        track_id = find_track_for_face(
            face,
            detections
        )


        # ====================================================
        # FACE BOX
        # ====================================================

        fx1, fy1, fx2, fy2 = map(
            int,
            face.bbox
        )


        # ====================================================
        # CASE 1
        # RECOGNIZED + TRACKED
        # ====================================================

        if (
            student_id is not None
            and
            track_id is not None
        ):

            # ------------------------------------------------
            # MARK ATTENDANCE
            # ------------------------------------------------

            newly_marked = (
                attendance_manager.mark_present(
                    student_id,
                    track_id,
                    similarity
                )
            )


            # ------------------------------------------------
            # Display label
            # ------------------------------------------------

            if newly_marked:

                attendance_text = "PRESENT"

            else:

                attendance_text = "PRESENT"


            label = (
                f"{student_id} | "
                f"Track {track_id} | "
                f"{similarity:.2f} | "
                f"{attendance_text}"
            )


            # ------------------------------------------------
            # Draw face box
            # ------------------------------------------------

            cv2.rectangle(
                frame,
                (fx1, fy1),
                (fx2, fy2),
                (255, 0, 0),
                2
            )


            # ------------------------------------------------
            # Draw label
            # ------------------------------------------------

            cv2.putText(
                frame,
                label,
                (
                    fx1,
                    max(
                        fy1 - 10,
                        20
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (255, 0, 0),
                2
            )


        # ====================================================
        # CASE 2
        # RECOGNIZED BUT NOT TRACKED
        # ====================================================

        elif student_id is not None:

            label = (
                f"{student_id} | "
                f"No Track | "
                f"{similarity:.2f}"
            )


            cv2.rectangle(
                frame,
                (fx1, fy1),
                (fx2, fy2),
                (0, 255, 255),
                2
            )


            cv2.putText(
                frame,
                label,
                (
                    fx1,
                    max(
                        fy1 - 10,
                        20
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 255, 255),
                2
            )


        # ====================================================
        # CASE 3
        # UNKNOWN FACE
        # ====================================================

        else:

            label = (
                f"Unknown | "
                f"{similarity:.2f}"
            )


            cv2.rectangle(
                frame,
                (fx1, fy1),
                (fx2, fy2),
                (0, 0, 255),
                2
            )


            cv2.putText(
                frame,
                label,
                (
                    fx1,
                    max(
                        fy1 - 10,
                        20
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 0, 255),
                2
            )


    # ========================================================
    # DRAW PERSON TRACK BOXES
    # ========================================================

    for i in range(
        len(detections)
    ):

        x1, y1, x2, y2 = map(
            int,
            detections.xyxy[i]
        )


        track_id = int(
            detections.tracker_id[i]
        )


        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )


        cv2.putText(
            frame,
            f"Track ID {track_id}",
            (
                x1,
                max(
                    y1 - 10,
                    20
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (0, 255, 0),
            2
        )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "AI Smart Classroom - Step 7 Attendance",
        frame
    )


    # ========================================================
    # EXIT
    # ========================================================

    key = cv2.waitKey(
        1
    ) & 0xFF


    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()


print("=" * 70)
print("STEP 7 STOPPED")
print("=" * 70)

print(
    f"Total Present Students: "
    f"{attendance_manager.get_present_count()}"
)

print(
    "Present Students:",
    attendance_manager.get_present_students()
)