import cv2
import numpy as np
import pickle
import json
import os
import time

from collections import defaultdict, deque
from datetime import datetime

from ultralytics import YOLO
import supervision as sv

from insightface.app import FaceAnalysis

from ai.attendance.attendance_manager import AttendanceManager
from ai.tracking.student_tracker import StudentTracker


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolov8m.pt"

EMBEDDINGS_FILE = "embeddings/face_embeddings.pkl"

CAMERA_INDEX = 0

# ------------------------------------------------------------
# YOLO SETTINGS
# ------------------------------------------------------------

PERSON_CONFIDENCE = 0.35
PERSON_IOU = 0.50
PERSON_IMAGE_SIZE = 960
MAX_PERSONS = 100

# ------------------------------------------------------------
# FACE RECOGNITION
# ------------------------------------------------------------

FACE_RECOGNITION_THRESHOLD = 0.50

# ------------------------------------------------------------
# ATTENTION SETTINGS
# ------------------------------------------------------------

MAX_YAW_RATIO = 0.22

MIN_PITCH_RATIO = 0.25
MAX_PITCH_RATIO = 0.72

ATTENTION_HISTORY_LENGTH = 7

ATTENTION_MIN_VALID_FRAMES = 2

# ------------------------------------------------------------
# FACE SIZE
# ------------------------------------------------------------

MIN_FACE_WIDTH = 35
MIN_FACE_HEIGHT = 35

# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------

DASHBOARD_STATE_FILE = "dashboard/classroom_state.json"

# Update dashboard file every 0.5 seconds.
DASHBOARD_UPDATE_INTERVAL = 0.5


# ============================================================
# GLOBAL ATTENTION STATE
# ============================================================

attention_history = defaultdict(
    lambda: deque(
        maxlen=ATTENTION_HISTORY_LENGTH
    )
)

last_attention_state = {}

last_attention_values = {}


# ============================================================
# DASHBOARD STATE
# ============================================================

last_dashboard_update = 0.0


def save_dashboard_state(
    tracked_persons,
    present_students,
    students
):
    """
    Save live classroom information.

    This file is consumed by STEP 10
    Classroom Dashboard.
    """

    try:

        dashboard_data = {
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "tracked_persons": int(
                tracked_persons
            ),

            "present_students": int(
                present_students
            ),

            "students": students
        }

        directory = os.path.dirname(
            DASHBOARD_STATE_FILE
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        temp_file = (
            DASHBOARD_STATE_FILE
            + ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                dashboard_data,
                file,
                indent=4
            )

        os.replace(
            temp_file,
            DASHBOARD_STATE_FILE
        )

    except Exception as error:

        print(
            f"[DASHBOARD] State update failed: {error}"
        )


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def draw_text_box(
    frame,
    text,
    position,
    text_color=(255, 255, 255),
    background_color=(30, 30, 30),
    font_scale=0.60,
    thickness=2,
    padding=6
):
    """
    Draw highly visible text with a filled background.
    """

    x, y = position

    font = cv2.FONT_HERSHEY_SIMPLEX

    (
        text_width,
        text_height
    ), baseline = cv2.getTextSize(
        text,
        font,
        font_scale,
        thickness
    )

    x1 = max(
        0,
        int(x - padding)
    )

    y1 = max(
        0,
        int(y - text_height - padding)
    )

    x2 = min(
        frame.shape[1] - 1,
        int(x + text_width + padding)
    )

    y2 = min(
        frame.shape[0] - 1,
        int(y + baseline + padding)
    )

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        background_color,
        -1
    )

    cv2.putText(
        frame,
        text,
        (int(x), int(y)),
        font,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA
    )


def clip_box(
    x1,
    y1,
    x2,
    y2,
    width,
    height
):
    """
    Keep bounding box inside image.
    """

    x1 = max(
        0,
        min(int(x1), width - 1)
    )

    y1 = max(
        0,
        min(int(y1), height - 1)
    )

    x2 = max(
        0,
        min(int(x2), width - 1)
    )

    y2 = max(
        0,
        min(int(y2), height - 1)
    )

    return x1, y1, x2, y2


def calculate_distance(
    point1,
    point2
):
    """
    Euclidean distance between two points.
    """

    return float(
        np.linalg.norm(
            np.asarray(
                point1,
                dtype=np.float32
            )
            -
            np.asarray(
                point2,
                dtype=np.float32
            )
        )
    )


# ============================================================
# ATTENTION SMOOTHING
# ============================================================

def smooth_attention(
    track_id,
    new_state
):
    """
    Smooth attention state.

    UNKNOWN states are ignored so one bad
    frame does not immediately change the
    student's attention state.
    """

    if new_state in (
        "ATTENTIVE",
        "NOT ATTENTIVE"
    ):

        history = attention_history[
            track_id
        ]

        history.append(
            new_state
        )

        counts = {}

        for state in history:

            counts[state] = (
                counts.get(
                    state,
                    0
                ) + 1
            )

        if not counts:

            return last_attention_state.get(
                track_id,
                "UNKNOWN"
            )

        best_state = max(
            counts,
            key=counts.get
        )

        if len(history) >= ATTENTION_MIN_VALID_FRAMES:

            last_attention_state[
                track_id
            ] = best_state

            return best_state

        return last_attention_state.get(
            track_id,
            best_state
        )

    return last_attention_state.get(
        track_id,
        "UNKNOWN"
    )


# ============================================================
# FACE EMBEDDING NORMALIZATION
# ============================================================

def normalize_embedding(
    embedding
):
    """
    Convert embedding into a normalized 1D vector.
    """

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    )

    embedding = embedding.reshape(-1)

    norm = np.linalg.norm(
        embedding
    )

    if norm == 0:

        return None

    return embedding / norm


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

    raw_embeddings = pickle.load(
        file
    )


known_embeddings = {}


for student_id, embeddings in raw_embeddings.items():

    student_vectors = []

    for embedding in embeddings:

        normalized = normalize_embedding(
            embedding
        )

        if normalized is not None:

            student_vectors.append(
                normalized
            )

    if student_vectors:

        known_embeddings[
            student_id
        ] = np.asarray(
            student_vectors,
            dtype=np.float32
        )


print("Known Students:")

for student_id, embeddings in known_embeddings.items():

    print(
        f"  - {student_id}: "
        f"{len(embeddings)} embeddings"
    )


# ============================================================
# FACE RECOGNITION
# ============================================================

def recognize_face(
    face_embedding
):
    """
    Compare detected face against all
    stored student embeddings.
    """

    query = normalize_embedding(
        face_embedding
    )

    if query is None:

        return None, 0.0

    best_student = None

    best_similarity = -1.0

    for student_id, embeddings in known_embeddings.items():

        for stored_embedding in embeddings:

            stored_embedding = normalize_embedding(
                stored_embedding
            )

            if stored_embedding is None:

                continue

            similarity = float(
                np.dot(
                    query,
                    stored_embedding
                )
            )

            if similarity > best_similarity:

                best_similarity = similarity

                best_student = student_id

    if (
        best_student is not None
        and
        best_similarity >=
        FACE_RECOGNITION_THRESHOLD
    ):

        return (
            best_student,
            best_similarity
        )

    return (
        None,
        best_similarity
    )


# ============================================================
# ATTENTION ESTIMATION
# ============================================================

def estimate_attention(
    face
):
    """
    Estimate attention using InsightFace
    five facial keypoints.

    Returns:

        state
        yaw_ratio
        pitch_ratio
    """

    if face is None:

        return (
            "UNKNOWN",
            None,
            None
        )

    if not hasattr(
        face,
        "kps"
    ):

        return (
            "UNKNOWN",
            None,
            None
        )

    kps = face.kps

    if kps is None:

        return (
            "UNKNOWN",
            None,
            None
        )

    try:

        points = np.asarray(
            kps,
            dtype=np.float32
        )

        if points.shape[0] < 5:

            return (
                "UNKNOWN",
                None,
                None
            )

        # ----------------------------------------------------
        # FIVE FACIAL LANDMARKS
        # ----------------------------------------------------

        left_eye = points[0]

        right_eye = points[1]

        nose = points[2]

        left_mouth = points[3]

        right_mouth = points[4]

        # ----------------------------------------------------
        # MIDPOINTS
        # ----------------------------------------------------

        eye_center = (
            left_eye +
            right_eye
        ) / 2.0

        mouth_center = (
            left_mouth +
            right_mouth
        ) / 2.0

        # ----------------------------------------------------
        # DISTANCES
        # ----------------------------------------------------

        eye_distance = calculate_distance(
            left_eye,
            right_eye
        )

        face_vertical_distance = calculate_distance(
            eye_center,
            mouth_center
        )

        if eye_distance < 5:

            return (
                "UNKNOWN",
                None,
                None
            )

        if face_vertical_distance < 5:

            return (
                "UNKNOWN",
                None,
                None
            )

        # ----------------------------------------------------
        # YAW
        # ----------------------------------------------------

        horizontal_offset = abs(
            float(
                nose[0] -
                eye_center[0]
            )
        )

        yaw_ratio = (
            horizontal_offset /
            eye_distance
        )

        # ----------------------------------------------------
        # PITCH
        # ----------------------------------------------------

        vertical_offset = float(
            nose[1] -
            eye_center[1]
        )

        pitch_ratio = (
            vertical_offset /
            face_vertical_distance
        )

        # ----------------------------------------------------
        # ROLL
        # ----------------------------------------------------

        eye_delta_y = float(
            right_eye[1] -
            left_eye[1]
        )

        eye_delta_x = float(
            right_eye[0] -
            left_eye[0]
        )

        roll_angle = np.degrees(
            np.arctan2(
                eye_delta_y,
                eye_delta_x
            )
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not np.isfinite(
            yaw_ratio
        ):

            return (
                "UNKNOWN",
                None,
                None
            )

        if not np.isfinite(
            pitch_ratio
        ):

            return (
                "UNKNOWN",
                None,
                None
            )

        # ----------------------------------------------------
        # ATTENTION DECISION
        # ----------------------------------------------------

        yaw_ok = (
            yaw_ratio <=
            MAX_YAW_RATIO
        )

        pitch_ok = (
            MIN_PITCH_RATIO
            <=
            pitch_ratio
            <=
            MAX_PITCH_RATIO
        )

        if yaw_ok and pitch_ok:

            state = "ATTENTIVE"

        else:

            state = "NOT ATTENTIVE"

        _ = roll_angle

        return (
            state,
            yaw_ratio,
            pitch_ratio
        )

    except Exception as error:

        print(
            f"[ATTENTION] Estimation error: {error}"
        )

        return (
            "UNKNOWN",
            None,
            None
        )


# ============================================================
# YOLO PERSON DETECTOR
# ============================================================

print("=" * 60)
print("Loading YOLO Person Detector...")
print("=" * 60)

model = YOLO(
    YOLO_MODEL
)

print(
    "YOLO Loaded Successfully."
)


# ============================================================
# BYTE TRACK
# ============================================================

print("=" * 60)
print("Loading ByteTrack...")
print("=" * 60)

tracker = sv.ByteTrack()

print(
    "ByteTrack Loaded Successfully."
)


# ============================================================
# ATTENDANCE MANAGER
# ============================================================

print("=" * 60)
print("Loading Attendance Manager...")
print("=" * 60)

attendance_manager = AttendanceManager()

print(
    "Attendance Manager Loaded Successfully."
)


# ============================================================
# STUDENT TRACKER
# ============================================================

print("=" * 60)
print("Loading Student Tracker...")
print("=" * 60)

student_tracker = StudentTracker()

print(
    "Student Tracker Loaded Successfully."
)


# ============================================================
# INSIGHTFACE
# ============================================================

print("=" * 60)
print("Loading InsightFace...")
print("=" * 60)

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=[
        "CPUExecutionProvider"
    ]
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print(
    "InsightFace Loaded Successfully."
)


# ============================================================
# CAMERA
# ============================================================

print("=" * 60)
print("Opening Camera...")
print("=" * 60)

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

    print(
        "ERROR: Cannot open camera."
    )

    raise SystemExit(1)


# ============================================================
# MAIN LOOP
# ============================================================

print("=" * 60)
print("AI SMART CLASSROOM")
print("STEP 9 - ATTENTION DETECTION")
print("=" * 60)

print(
    "Face + Person + ByteTrack + "
    "Student Association + Attendance + Attention"
)

print(
    "Dashboard state will be updated at:"
)

print(
    DASHBOARD_STATE_FILE
)

print(
    "Press Q to exit."
)

print("=" * 60)


tracked_person_count = 0

present_students = 0

while True:

    success, frame = camera.read()

    if not success:

        print(
            "Camera frame read failed."
        )

        break

    frame_height, frame_width = (
        frame.shape[:2]
    )

    # --------------------------------------------------------
    # YOLO PERSON DETECTION
    # --------------------------------------------------------

    results = model(
        frame,
        classes=[0],
        conf=PERSON_CONFIDENCE,
        iou=PERSON_IOU,
        imgsz=PERSON_IMAGE_SIZE,
        max_det=MAX_PERSONS,
        verbose=False
    )[0]

    detections = (
        sv.Detections.from_ultralytics(
            results
        )
    )

    # --------------------------------------------------------
    # PERSON CLASS ONLY
    # --------------------------------------------------------

    if len(detections) > 0:

        detections = detections[
            detections.class_id == 0
        ]

    # --------------------------------------------------------
    # BYTE TRACK
    # --------------------------------------------------------

    detections = (
        tracker.update_with_detections(
            detections
        )
    )

    tracked_person_count = len(
        detections
    )

    # --------------------------------------------------------
    # CURRENT TRACKS
    # --------------------------------------------------------

    current_tracks = set()

    # --------------------------------------------------------
    # DASHBOARD STUDENT LIST
    # --------------------------------------------------------

    dashboard_students = []

    # --------------------------------------------------------
    # PROCESS EACH PERSON
    # --------------------------------------------------------

    for index in range(
        len(detections)
    ):

        if detections.tracker_id is None:

            continue

        track_id = int(
            detections.tracker_id[index]
        )

        current_tracks.add(
            track_id
        )

        # ----------------------------------------------------
        # PERSON BOX
        # ----------------------------------------------------

        x1, y1, x2, y2 = map(
            int,
            detections.xyxy[index]
        )

        x1, y1, x2, y2 = clip_box(
            x1,
            y1,
            x2,
            y2,
            frame_width,
            frame_height
        )

        if x2 <= x1 or y2 <= y1:

            continue

        # ----------------------------------------------------
        # PERSON CROP
        # ----------------------------------------------------

        person_crop = frame[
            y1:y2,
            x1:x2
        ]

        if person_crop.size == 0:

            continue

        # ----------------------------------------------------
        # EXISTING STUDENT ASSOCIATION
        # ----------------------------------------------------

        known_student = None

        try:

            known_student = (
                student_tracker.update_track(
                    track_id
                )
            )

        except Exception as error:

            print(
                f"[TRACKER] update error: {error}"
            )

            known_student = None

        recognized_id = known_student

        similarity = 0.0

        # ----------------------------------------------------
        # FACE DETECTION
        # ----------------------------------------------------

        faces = []

        try:

            faces = face_app.get(
                person_crop
            )

        except Exception as error:

            print(
                f"[FACE] Detection error: {error}"
            )

            faces = []

        # ----------------------------------------------------
        # FIND BEST FACE
        # ----------------------------------------------------

        best_face = None

        best_face_area = 0

        for face in faces:

            try:

                fx1, fy1, fx2, fy2 = map(
                    int,
                    face.bbox
                )

                face_width = (
                    fx2 - fx1
                )

                face_height = (
                    fy2 - fy1
                )

                if (
                    face_width <
                    MIN_FACE_WIDTH
                    or
                    face_height <
                    MIN_FACE_HEIGHT
                ):

                    continue

                face_center_x = (
                    fx1 + fx2
                ) / 2.0

                face_center_y = (
                    fy1 + fy2
                ) / 2.0

                crop_width = (
                    person_crop.shape[1]
                )

                crop_height = (
                    person_crop.shape[0]
                )

                if not (
                    0 <= face_center_x
                    <= crop_width
                    and
                    0 <= face_center_y
                    <= crop_height
                ):

                    continue

                area = (
                    face_width *
                    face_height
                )

                if area > best_face_area:

                    best_face = face

                    best_face_area = area

            except Exception:

                continue

        # ----------------------------------------------------
        # FACE RECOGNITION
        # ----------------------------------------------------

        if best_face is not None:

            try:

                if hasattr(
                    best_face,
                    "embedding"
                ):

                    (
                        newly_recognized_id,
                        newly_similarity
                    ) = recognize_face(
                        best_face.embedding
                    )

                    if newly_recognized_id is not None:

                        recognized_id = (
                            newly_recognized_id
                        )

                        similarity = (
                            newly_similarity
                        )

            except Exception as error:

                print(
                    f"[RECOGNITION] Error: {error}"
                )

        # ----------------------------------------------------
        # STUDENT ASSOCIATION
        # ----------------------------------------------------

        if recognized_id is not None:

            try:

                student_tracker.associate(
                    track_id,
                    recognized_id,
                    similarity
                )

            except Exception as error:

                print(
                    f"[TRACKER] Association error: {error}"
                )

            # ------------------------------------------------
            # ATTENDANCE
            # ------------------------------------------------

            try:

                attendance_manager.mark_present(
                    recognized_id,
                    track_id,
                    similarity
                )

            except Exception as error:

                print(
                    f"[ATTENDANCE] Error: {error}"
                )

        # ----------------------------------------------------
        # ATTENTION
        # ----------------------------------------------------

        raw_attention_state = "UNKNOWN"

        yaw_ratio = None

        pitch_ratio = None

        if best_face is not None:

            (
                raw_attention_state,
                yaw_ratio,
                pitch_ratio
            ) = estimate_attention(
                best_face
            )

        # ----------------------------------------------------
        # SMOOTH ATTENTION
        # ----------------------------------------------------

        attention_state = smooth_attention(
            track_id,
            raw_attention_state
        )

        # ----------------------------------------------------
        # STORE LAST NUMERIC VALUES
        # ----------------------------------------------------

        if (
            yaw_ratio is not None
            and
            pitch_ratio is not None
        ):

            last_attention_values[
                track_id
            ] = (
                yaw_ratio,
                pitch_ratio
            )

        elif track_id in last_attention_values:

            (
                yaw_ratio,
                pitch_ratio
            ) = last_attention_values[
                track_id
            ]

        # ----------------------------------------------------
        # DASHBOARD STUDENT DATA
        # ----------------------------------------------------

        dashboard_student_id = None

        if recognized_id is not None:

            dashboard_student_id = str(
                recognized_id
            )

        student_record = {
            "track_id": int(
                track_id
            ),

            "student_id": dashboard_student_id,

            "recognized": (
                recognized_id is not None
            ),

            "similarity": round(
                float(similarity),
                3
            ),

            "attention": str(
                attention_state
            ),

            "yaw_ratio": (
                round(
                    float(yaw_ratio),
                    3
                )
                if yaw_ratio is not None
                else None
            ),

            "pitch_ratio": (
                round(
                    float(pitch_ratio),
                    3
                )
                if pitch_ratio is not None
                else None
            )
        }

        dashboard_students.append(
            student_record
        )

        # ----------------------------------------------------
        # PERSON BOX COLOR
        # ----------------------------------------------------

        if recognized_id is not None:

            person_box_color = (
                255,
                220,
                0
            )

        else:

            person_box_color = (
                0,
                165,
                255
            )

        # ----------------------------------------------------
        # ATTENTION COLOR
        # ----------------------------------------------------

        if attention_state == "ATTENTIVE":

            attention_color = (
                0,
                255,
                0
            )

            attention_background = (
                20,
                90,
                20
            )

        elif attention_state == "NOT ATTENTIVE":

            attention_color = (
                0,
                0,
                255
            )

            attention_background = (
                90,
                20,
                20
            )

        else:

            attention_color = (
                255,
                255,
                255
            )

            attention_background = (
                70,
                55,
                20
            )

        # ----------------------------------------------------
        # DRAW PERSON BOX
        # ----------------------------------------------------

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            person_box_color,
            2
        )

        # ----------------------------------------------------
        # IDENTITY LABEL
        # ----------------------------------------------------

        if recognized_id is not None:

            identity_text = (
                f"ID {track_id} | "
                f"{recognized_id}"
            )

        else:

            identity_text = (
                f"ID {track_id} | UNKNOWN"
            )

        label_x = max(
            8,
            x1
        )

        label_y = max(
            30,
            y1 + 28
        )

        draw_text_box(
            frame,
            identity_text,
            (
                label_x,
                label_y
            ),
            text_color=(
                255,
                255,
                255
            ),
            background_color=(
                25,
                35,
                40
            ),
            font_scale=0.58,
            thickness=2,
            padding=6
        )

        # ----------------------------------------------------
        # ATTENTION LABEL
        # ----------------------------------------------------

        attention_text = (
            f"Attention: "
            f"{attention_state}"
        )

        attention_y = (
            label_y + 38
        )

        draw_text_box(
            frame,
            attention_text,
            (
                label_x,
                attention_y
            ),
            text_color=attention_color,
            background_color=attention_background,
            font_scale=0.58,
            thickness=2,
            padding=6
        )

        # ----------------------------------------------------
        # FACE BOX
        # ----------------------------------------------------

        if best_face is not None:

            try:

                fx1, fy1, fx2, fy2 = map(
                    int,
                    best_face.bbox
                )

                fx1 += x1
                fx2 += x1

                fy1 += y1
                fy2 += y1

                fx1, fy1, fx2, fy2 = clip_box(
                    fx1,
                    fy1,
                    fx2,
                    fy2,
                    frame_width,
                    frame_height
                )

                cv2.rectangle(
                    frame,
                    (fx1, fy1),
                    (fx2, fy2),
                    (
                        255,
                        80,
                        0
                    ),
                    2
                )

                if recognized_id is not None:

                    face_text = (
                        f"{recognized_id} "
                        f"{similarity:.2f}"
                    )

                else:

                    face_text = (
                        "Unknown Face"
                    )

                face_label_y = max(
                    25,
                    fy1 - 8
                )

                draw_text_box(
                    frame,
                    face_text,
                    (
                        fx1,
                        face_label_y
                    ),
                    text_color=(
                        255,
                        255,
                        255
                    ),
                    background_color=(
                        25,
                        25,
                        25
                    ),
                    font_scale=0.52,
                    thickness=2,
                    padding=5
                )

            except Exception:

                pass

    # ========================================================
    # PRESENT STUDENTS
    # ========================================================

    try:

        present_students = len(
            attendance_manager
            .get_present_students()
        )

    except Exception:

        present_students = 0

    # ========================================================
    # UPDATE DASHBOARD STATE
    # ========================================================

    current_time = time.time()

    if (
        current_time -
        last_dashboard_update
        >=
        DASHBOARD_UPDATE_INTERVAL
    ):

        save_dashboard_state(
            tracked_person_count,
            present_students,
            dashboard_students
        )

        last_dashboard_update = (
            current_time
        )

    # ========================================================
    # DASHBOARD HEADER
    # ========================================================

    dashboard_height = 118

    dashboard_width = 410

    cv2.rectangle(
        frame,
        (0, 0),
        (
            dashboard_width,
            dashboard_height
        ),
        (
            18,
            18,
            18
        ),
        -1
    )

    cv2.rectangle(
        frame,
        (0, 0),
        (
            dashboard_width,
            dashboard_height
        ),
        (
            70,
            70,
            70
        ),
        1
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    cv2.putText(
        frame,
        "AI SMART CLASSROOM - STEP 9",
        (15, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (
            255,
            255,
            255
        ),
        2,
        cv2.LINE_AA
    )

    # --------------------------------------------------------
    # TRACKED PERSONS
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"Tracked Persons: "
        f"{tracked_person_count}",
        (15, 63),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (
            0,
            255,
            0
        ),
        2,
        cv2.LINE_AA
    )

    # --------------------------------------------------------
    # PRESENT STUDENTS
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"Present Students: "
        f"{present_students}",
        (15, 94),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (
            0,
            220,
            255
        ),
        2,
        cv2.LINE_AA
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "AI Smart Classroom - Attention Detection",
        frame
    )

    # ========================================================
    # KEYBOARD
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()


# ============================================================
# FINAL OUTPUT
# ============================================================

print("=" * 60)

print(
    "STEP 9 STOPPED"
)

print("=" * 60)

print(
    f"Tracked persons in final frame: "
    f"{tracked_person_count}"
)

print(
    f"Present students: "
    f"{present_students}"
)

print(
    f"Dashboard state: "
    f"{DASHBOARD_STATE_FILE}"
)

print("=" * 60)