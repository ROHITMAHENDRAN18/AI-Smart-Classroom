import cv2
import pickle
import numpy as np

from ultralytics import YOLO
import supervision as sv

from insightface.app import FaceAnalysis

from ai.attendance.attendance_manager import AttendanceManager
from ai.tracking.student_tracker import StudentTracker


# ============================================================
# STEP 9
# AI SMART CLASSROOM
# FACE + PERSON + TRACK + ATTENDANCE + ATTENTION
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolov8m.pt"

EMBEDDING_FILE = "embeddings/face_embeddings.pkl"

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

FACE_SIMILARITY_THRESHOLD = 0.45

# Number of consecutive frames required before
# changing the attention state.
ATTENTION_CONFIRM_FRAMES = 5


# ============================================================
# LOAD YOLO
# ============================================================

print("=" * 70)
print("Loading YOLO Person Detector...")
print("=" * 70)

model = YOLO(YOLO_MODEL)

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
# LOAD ATTENDANCE MANAGER
# ============================================================

print("=" * 70)
print("Loading Attendance Manager...")
print("=" * 70)

attendance_manager = AttendanceManager()

print("Attendance Manager Loaded Successfully.")


# ============================================================
# LOAD STUDENT TRACKER
# ============================================================

print("=" * 70)
print("Loading Student Tracker...")
print("=" * 70)

student_tracker = StudentTracker()

print("Student Tracker Loaded Successfully.")


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

    database = pickle.load(file)


print("Known Students:")

for student_id, embeddings in database.items():

    print(
        f"  - {student_id}: "
        f"{len(embeddings)} embeddings"
    )


# ============================================================
# NORMALIZE EMBEDDINGS
# ============================================================

normalized_database = {}

for student_id, embeddings in database.items():

    normalized_embeddings = []

    for embedding in embeddings:

        embedding = np.asarray(
            embedding,
            dtype=np.float32
        )

        norm = np.linalg.norm(embedding)

        if norm > 0:

            embedding = embedding / norm

        normalized_embeddings.append(
            embedding
        )

    normalized_database[student_id] = (
        normalized_embeddings
    )


# ============================================================
# FACE RECOGNITION FUNCTION
# ============================================================

def recognize_face(face_embedding):

    face_embedding = np.asarray(
        face_embedding,
        dtype=np.float32
    )

    norm = np.linalg.norm(face_embedding)

    if norm == 0:

        return None, 0.0

    face_embedding = face_embedding / norm

    best_student = None
    best_similarity = -1.0

    for student_id, embeddings in normalized_database.items():

        for saved_embedding in embeddings:

            similarity = float(
                np.dot(
                    face_embedding,
                    saved_embedding
                )
            )

            if similarity > best_similarity:

                best_similarity = similarity
                best_student = student_id

    if best_similarity < FACE_SIMILARITY_THRESHOLD:

        return None, best_similarity

    return best_student, best_similarity


# ============================================================
# ATTENTION STATE STORAGE
# ============================================================

attention_states = {}

attention_counters = {}


# ============================================================
# ATTENTION FUNCTION
# ============================================================

def estimate_attention(
    person_box,
    face_box
):

    px1, py1, px2, py2 = person_box

    fx1, fy1, fx2, fy2 = face_box

    person_width = px2 - px1
    person_height = py2 - py1

    if person_width <= 0 or person_height <= 0:

        return "UNKNOWN"

    # Face center

    face_center_x = (fx1 + fx2) / 2
    face_center_y = (fy1 + fy2) / 2

    # Normalize face position
    # inside the person bounding box.

    relative_x = (
        face_center_x - px1
    ) / person_width

    relative_y = (
        face_center_y - py1
    ) / person_height

    # --------------------------------------------------------
    # Basic visibility check
    # --------------------------------------------------------

    if (
        relative_x < 0
        or relative_x > 1
        or relative_y < 0
        or relative_y > 1
    ):

        return "UNKNOWN"

    # --------------------------------------------------------
    # Approximate head orientation
    #
    # This is intentionally conservative.
    # It does NOT claim a trained head-pose model.
    # --------------------------------------------------------

    if 0.25 <= relative_x <= 0.75:

        return "ATTENTIVE"

    return "NOT ATTENTIVE"


# ============================================================
# FIND FACE INSIDE PERSON
# ============================================================

def find_face_for_person(
    person_box,
    faces
):

    px1, py1, px2, py2 = person_box

    best_face = None
    best_area = 0

    for face in faces:

        fx1, fy1, fx2, fy2 = (
            face.bbox.astype(int)
        )

        face_center_x = (
            fx1 + fx2
        ) / 2

        face_center_y = (
            fy1 + fy2
        ) / 2

        # Check whether face center
        # lies inside person box.

        if (
            px1 <= face_center_x <= px2
            and
            py1 <= face_center_y <= py2
        ):

            area = (
                fx2 - fx1
            ) * (
                fy2 - fy1
            )

            if area > best_area:

                best_area = area
                best_face = face

    return best_face


# ============================================================
# OPEN CAMERA
# ============================================================

print("=" * 70)
print("Opening Camera...")
print("=" * 70)

camera = cv2.VideoCapture(0)

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    CAMERA_WIDTH
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    CAMERA_HEIGHT
)

if not camera.isOpened():

    print("ERROR: Cannot Open Camera")

    raise SystemExit


# ============================================================
# START
# ============================================================

print("=" * 70)
print("AI SMART CLASSROOM")
print("STEP 9 - ATTENTION DETECTION")
print("=" * 70)

print(
    "Face + Person + ByteTrack + "
    "Student Association + Attendance + Attention"
)

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
    # YOLO PERSON DETECTION
    # ========================================================

    results = model(
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
    # PERSON ONLY
    # ========================================================

    if detections.class_id is not None:

        detections = detections[
            detections.class_id == 0
        ]


    # ========================================================
    # BYTE TRACK
    # ========================================================

    detections = tracker.update_with_detections(
        detections
    )


    # ========================================================
    # INSIGHTFACE
    # ========================================================

    faces = face_app.get(frame)


    # ========================================================
    # PROCESS EVERY TRACK
    # ========================================================

    for index in range(
        len(detections)
    ):

        # ----------------------------------------------------
        # PERSON BOX
        # ----------------------------------------------------

        x1, y1, x2, y2 = (
            detections.xyxy[index].astype(int)
        )


        # ----------------------------------------------------
        # TRACK ID
        # ----------------------------------------------------

        track_id = int(
            detections.tracker_id[index]
        )


        person_box = (
            x1,
            y1,
            x2,
            y2
        )


        # ----------------------------------------------------
        # FIND FACE
        # ----------------------------------------------------

        matched_face = find_face_for_person(
            person_box,
            faces
        )


        recognized_id = None
        similarity = 0.0

        attention = "UNKNOWN"


        # ====================================================
        # FACE FOUND
        # ====================================================

        if matched_face is not None:

            # ------------------------------------------------
            # FACE EMBEDDING
            # ------------------------------------------------

            embedding = matched_face.embedding


            # ------------------------------------------------
            # RECOGNIZE STUDENT
            # ------------------------------------------------

            recognized_id, similarity = (
                recognize_face(
                    embedding
                )
            )


            # ------------------------------------------------
            # STUDENT TRACK ASSOCIATION
            # ------------------------------------------------

            if recognized_id is not None:

                student_tracker.associate(
                    track_id,
                    recognized_id,
                    similarity
                )


                # --------------------------------------------
                # ATTENDANCE
                # --------------------------------------------

                attendance_manager.mark_present(
                    recognized_id,
                    track_id,
                    similarity
                )


            # ------------------------------------------------
            # ATTENTION
            # ------------------------------------------------

            face_box = (
                *matched_face.bbox.astype(int),
            )

            attention = estimate_attention(
                person_box,
                face_box
            )


        # ====================================================
        # CHECK EXISTING TRACK ASSOCIATION
        # ====================================================

        known_student = (
            student_tracker.update_track(
                track_id
            )
        )


        if (
            recognized_id is None
            and
            known_student is not None
        ):

            recognized_id = known_student


            try:

                similarity = (
                    student_tracker
                    .get_similarity(
                        track_id
                    )
                )

            except Exception:

                similarity = 0.0


        # ====================================================
        # STABILIZE ATTENTION
        # ====================================================

        if track_id not in attention_counters:

            attention_counters[track_id] = {
                "state": "UNKNOWN",
                "count": 0
            }


        current_state = attention


        previous_state = (
            attention_counters[track_id]["state"]
        )


        if current_state == previous_state:

            attention_counters[track_id]["count"] += 1

        else:

            attention_counters[track_id]["state"] = (
                current_state
            )

            attention_counters[track_id]["count"] = 1


        if (
            attention_counters[track_id]["count"]
            >= ATTENTION_CONFIRM_FRAMES
        ):

            attention_states[track_id] = (
                current_state
            )


        stable_attention = attention_states.get(
            track_id,
            "UNKNOWN"
        )


        # ====================================================
        # LABEL
        # ====================================================

        if recognized_id is not None:

            student_label = recognized_id

        else:

            student_label = "Unknown"


        label = (
            f"ID {track_id} | "
            f"{student_label}"
        )


        attention_label = (
            f"Attention: {stable_attention}"
        )


        # ====================================================
        # BOX COLOR
        # ====================================================

        if recognized_id is not None:

            if stable_attention == "ATTENTIVE":

                color = (
                    0,
                    255,
                    0
                )

            elif stable_attention == "NOT ATTENTIVE":

                color = (
                    0,
                    0,
                    255
                )

            else:

                color = (
                    0,
                    255,
                    255
                )

        else:

            color = (
                128,
                128,
                128
            )


        # ====================================================
        # DRAW PERSON BOX
        # ====================================================

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )


        # ====================================================
        # DRAW STUDENT LABEL
        # ====================================================

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 30, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2
        )


        # ====================================================
        # DRAW ATTENTION
        # ====================================================

        cv2.putText(
            frame,
            attention_label,
            (x1, y2 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )


        # ====================================================
        # DRAW SIMILARITY
        # ====================================================

        if recognized_id is not None:

            similarity_text = (
                f"Similarity: {similarity:.3f}"
            )

            cv2.putText(
                frame,
                similarity_text,
                (x1, y2 + 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 0),
                2
            )


    # ========================================================
    # GLOBAL TITLE
    # ========================================================

    cv2.putText(
        frame,
        "AI SMART CLASSROOM - STEP 9",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SHOW FRAME
    # ========================================================

    cv2.imshow(
        "AI Smart Classroom - Attention Detection",
        frame
    )


    # ========================================================
    # EXIT
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()


print("=" * 70)
print("STEP 9 STOPPED")
print("=" * 70)

print("Attention states:")

for track_id, state in attention_states.items():

    print(
        f"Track ID {track_id}: {state}"
    )