import cv2
import pickle
import numpy as np

from ultralytics import YOLO
import supervision as sv

from insightface.app import FaceAnalysis


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolov8m.pt"

EMBEDDINGS_FILE = "embeddings/face_embeddings.pkl"

CAMERA_INDEX = 0

FACE_THRESHOLD = 0.45


# ============================================================
# LOAD YOLO
# ============================================================

print("=" * 60)
print("Loading YOLOv8...")
print("=" * 60)

yolo = YOLO(YOLO_MODEL)

print("YOLOv8 Loaded Successfully.")


# ============================================================
# LOAD BYTETRACK
# ============================================================

print("=" * 60)
print("Initializing ByteTrack...")
print("=" * 60)

tracker = sv.ByteTrack()

print("ByteTrack Initialized Successfully.")


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print("=" * 60)
print("Loading InsightFace...")
print("=" * 60)

face_app = FaceAnalysis(
    name="buffalo_l"
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("InsightFace Loaded Successfully.")


# ============================================================
# LOAD FACE EMBEDDINGS
# ============================================================

print("=" * 60)
print("Loading Face Embeddings...")
print("=" * 60)

with open(
    EMBEDDINGS_FILE,
    "rb"
) as file:

    face_data = pickle.load(file)

print("Face Embeddings Loaded Successfully.")


# ============================================================
# CHECK EMBEDDING FORMAT
# ============================================================

print("Embedding data type:", type(face_data))

if isinstance(face_data, dict):

    print(
        "Known Students:",
        list(face_data.keys())
    )


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    a = np.asarray(a)

    b = np.asarray(b)

    denominator = (
        np.linalg.norm(a)
        *
        np.linalg.norm(b)
    )

    if denominator == 0:

        return 0.0

    return np.dot(a, b) / denominator


# ============================================================
# FACE RECOGNITION FUNCTION
# ============================================================

def recognize_face(face_embedding):

    best_student = "Unknown"

    best_score = 0.0

    if not isinstance(face_data, dict):

        return best_student, best_score

    for student_id, stored_embedding in face_data.items():

        # --------------------------------------------
        # Handle possible embedding structures
        # --------------------------------------------

        if isinstance(
            stored_embedding,
            dict
        ):

            if "embedding" in stored_embedding:

                stored_embedding = (
                    stored_embedding["embedding"]
                )

        score = cosine_similarity(
            face_embedding,
            stored_embedding
        )

        if score > best_score:

            best_score = score

            best_student = student_id

    if best_score < FACE_THRESHOLD:

        best_student = "Unknown"

    return best_student, best_score


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(
    CAMERA_INDEX
)

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)


if not camera.isOpened():

    print("❌ Cannot Open Camera")

    exit()


print("=" * 60)
print("Face + Person Tracking Started")
print("Press Q to Exit")
print("=" * 60)


# ============================================================
# TRACK → FACE ASSOCIATION
# ============================================================

track_student_map = {}


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print("❌ Failed to Read Frame")

        break


    # ========================================================
    # YOLO PERSON DETECTION
    # ========================================================

    results = yolo(
        frame,
        classes=[0],
        conf=0.35,
        iou=0.50,
        imgsz=960,
        max_det=100,
        verbose=False
    )[0]


    # ========================================================
    # CONVERT TO SUPERVISION
    # ========================================================

    detections = sv.Detections.from_ultralytics(
        results
    )


    # ========================================================
    # BYTE TRACK
    # ========================================================

    detections = tracker.update_with_detections(
        detections
    )


    # ========================================================
    # PROCESS EACH TRACK
    # ========================================================

    for i in range(len(detections)):

        # ----------------------------------------------------
        # Bounding box
        # ----------------------------------------------------

        x1, y1, x2, y2 = (
            detections.xyxy[i].astype(int)
        )


        # ----------------------------------------------------
        # Track ID
        # ----------------------------------------------------

        track_id = detections.tracker_id[i]


        if track_id is None:

            continue


        # ----------------------------------------------------
        # Make sure coordinates are valid
        # ----------------------------------------------------

        x1 = max(0, x1)
        y1 = max(0, y1)

        x2 = min(
            frame.shape[1],
            x2
        )

        y2 = min(
            frame.shape[0],
            y2
        )


        if x2 <= x1 or y2 <= y1:

            continue


        # ====================================================
        # CROP PERSON
        # ====================================================

        person_crop = frame[
            y1:y2,
            x1:x2
        ]


        if person_crop.size == 0:

            continue


        # ====================================================
        # FACE DETECTION
        # ====================================================

        faces = face_app.get(
            person_crop
        )


        # ====================================================
        # RECOGNIZE FACE
        # ====================================================

        student_id = "Unknown"

        face_score = 0.0


        if len(faces) > 0:

            # Use largest face
            face = max(
                faces,
                key=lambda f:
                (f.bbox[2] - f.bbox[0])
                *
                (f.bbox[3] - f.bbox[1])
            )


            embedding = face.embedding


            student_id, face_score = (
                recognize_face(
                    embedding
                )
            )


            # --------------------------------------------
            # Store association
            # --------------------------------------------

            if student_id != "Unknown":

                track_student_map[
                    int(track_id)
                ] = student_id


        # ====================================================
        # USE PREVIOUSLY RECOGNIZED STUDENT
        # ====================================================

        if (
            int(track_id)
            in track_student_map
        ):

            student_id = track_student_map[
                int(track_id)
            ]


        # ====================================================
        # DISPLAY LABEL
        # ====================================================

        if student_id != "Unknown":

            label = (
                f"ID {track_id} | "
                f"{student_id}"
            )

        else:

            label = (
                f"ID {track_id} | "
                f"Unknown"
            )


        # ====================================================
        # DRAW BOX
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
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "AI Smart Classroom - Face Tracking",
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

print("Face + Tracking Stopped.")