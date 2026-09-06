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

EMBEDDING_FILE = "embeddings/face_embeddings.pkl"

CAMERA_INDEX = 0

CONFIDENCE_THRESHOLD = 0.35

IOU_THRESHOLD = 0.50

IMAGE_SIZE = 960

FACE_MATCH_THRESHOLD = 0.45


# ============================================================
# LOAD YOLO PERSON DETECTOR
# ============================================================

print("=" * 70)
print("Loading YOLO Person Detector...")
print("=" * 70)

person_model = YOLO(YOLO_MODEL)

print("YOLO Loaded Successfully.")


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

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("InsightFace Loaded Successfully.")


# ============================================================
# LOAD FACE EMBEDDINGS
# ============================================================

print("=" * 70)
print("Loading Face Embeddings...")
print("=" * 70)

with open(EMBEDDING_FILE, "rb") as file:
    known_embeddings = pickle.load(file)

print("Known Students:")

for student_id in known_embeddings.keys():
    print("  -", student_id)

print("=" * 70)


# ============================================================
# NORMALIZE EMBEDDING
# ============================================================

def normalize_embedding(embedding):

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    )

    norm = np.linalg.norm(embedding)

    if norm == 0:
        return embedding

    return embedding / norm


# ============================================================
# PREPARE KNOWN EMBEDDINGS
# ============================================================

normalized_known_embeddings = {}

for student_id, embedding in known_embeddings.items():

    normalized_known_embeddings[
        student_id
    ] = normalize_embedding(embedding)


# ============================================================
# FACE RECOGNITION
# ============================================================

def recognize_face(face_embedding):

    face_embedding = normalize_embedding(
        face_embedding
    )

    best_student = None
    best_score = -1.0

    for student_id, known_embedding in normalized_known_embeddings.items():

        score = float(
            np.dot(
                face_embedding,
                known_embedding
            )
        )

        if score > best_score:

            best_score = score
            best_student = student_id

    if best_score >= FACE_MATCH_THRESHOLD:

        return best_student, best_score

    return "Unknown", best_score


# ============================================================
# CHECK FACE INSIDE PERSON TRACK
# ============================================================

def face_center_inside_box(face_box, person_box):

    fx1, fy1, fx2, fy2 = face_box

    px1, py1, px2, py2 = person_box

    face_center_x = (fx1 + fx2) / 2
    face_center_y = (fy1 + fy2) / 2

    return (
        px1 <= face_center_x <= px2
        and
        py1 <= face_center_y <= py2
    )


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

    print("ERROR: Cannot open camera.")

    raise SystemExit


print("=" * 70)
print("AI SMART CLASSROOM")
print("STEP 6 - FACE + TRACK ASSOCIATION")
print("=" * 70)
print("Press Q to exit.")
print("=" * 70)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print("ERROR: Failed to read camera frame.")

        break


    # ========================================================
    # PERSON DETECTION
    # ========================================================

    results = person_model(
        frame,
        classes=[0],
        conf=CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
        imgsz=IMAGE_SIZE,
        max_det=50,
        verbose=False
    )[0]


    # ========================================================
    # CONVERT YOLO → SUPERVISION
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
    # FACE DETECTION
    # ========================================================

    faces = face_app.get(frame)


    # ========================================================
    # STORE ASSOCIATIONS
    # ========================================================

    track_information = []


    # ========================================================
    # PROCESS EACH TRACK
    # ========================================================

    if detections.tracker_id is not None:

        for index, track_id in enumerate(
            detections.tracker_id
        ):

            person_box = detections.xyxy[index]

            px1, py1, px2, py2 = map(
                int,
                person_box
            )


            student_id = "Unknown"

            recognition_score = 0.0

            matched_face_box = None


            # =================================================
            # CHECK EVERY FACE
            # =================================================

            for face in faces:

                face_box = face.bbox

                face_embedding = face.embedding


                # =============================================
                # CHECK WHETHER FACE BELONGS TO THIS TRACK
                # =============================================

                if not face_center_inside_box(
                    face_box,
                    person_box
                ):

                    continue


                # =============================================
                # RECOGNIZE FACE
                # =============================================

                recognized_id, score = recognize_face(
                    face_embedding
                )


                # =============================================
                # KEEP BEST MATCH
                # =============================================

                if score > recognition_score:

                    student_id = recognized_id

                    recognition_score = score

                    matched_face_box = face_box


            # =================================================
            # SAVE TRACK INFORMATION
            # =================================================

            track_information.append(
                (
                    track_id,
                    px1,
                    py1,
                    px2,
                    py2,
                    student_id,
                    recognition_score,
                    matched_face_box
                )
            )


    # ========================================================
    # DRAW TRACKS
    # ========================================================

    for information in track_information:

        (
            track_id,
            px1,
            py1,
            px2,
            py2,
            student_id,
            recognition_score,
            face_box
        ) = information


        # ====================================================
        # PERSON TRACK BOX
        # ====================================================

        cv2.rectangle(
            frame,
            (px1, py1),
            (px2, py2),
            (0, 255, 0),
            2
        )


        # ====================================================
        # STUDENT LABEL
        # ====================================================

        if student_id != "Unknown":

            label = (
                f"{student_id} | "
                f"Track ID: {track_id} | "
                f"Face: {recognition_score:.2f}"
            )

        else:

            label = (
                f"Unknown | "
                f"Track ID: {track_id}"
            )


        # ====================================================
        # LABEL BACKGROUND
        # ====================================================

        (text_width, text_height), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            2
        )


        cv2.rectangle(
            frame,
            (px1, max(0, py1 - text_height - 12)),
            (
                px1 + text_width + 10,
                py1
            ),
            (0, 255, 0),
            -1
        )


        # ====================================================
        # LABEL TEXT
        # ====================================================

        cv2.putText(
            frame,
            label,
            (
                px1 + 5,
                py1 - 7
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            2
        )


        # ====================================================
        # DRAW FACE BOX
        # ====================================================

        if face_box is not None:

            fx1, fy1, fx2, fy2 = map(
                int,
                face_box
            )


            cv2.rectangle(
                frame,
                (fx1, fy1),
                (fx2, fy2),
                (255, 0, 0),
                2
            )


            cv2.putText(
                frame,
                "Face",
                (
                    fx1,
                    max(20, fy1 - 8)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 0, 0),
                2
            )


    # ========================================================
    # TRACK COUNT
    # ========================================================

    tracked_count = len(
        track_information
    )


    cv2.putText(
        frame,
        f"Tracked Persons: {tracked_count}",
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        3
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
print("Step 6 stopped.")
print("=" * 70)