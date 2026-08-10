import cv2
import pickle
import numpy as np

from insightface.app import FaceAnalysis
from ai.attendance.attendance_manager import AttendanceManager

# =====================================================
# Load InsightFace
# =====================================================

print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("Model Loaded Successfully.")

# =====================================================
# Load Database
# =====================================================

with open("embeddings/face_embeddings.pkl", "rb") as file:
    database = pickle.load(file)

print(f"{len(database)} Student(s) Loaded.")

# =====================================================
# Attendance Manager
# =====================================================

attendance = AttendanceManager()

# =====================================================
# Webcam
# =====================================================

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not camera.isOpened():
    print("Cannot Open Camera")
    exit()

print("=" * 60)
print("Real-Time Face Recognition Started")
print("Press Q to Exit")
print("=" * 60)

# =====================================================
# Threshold
# =====================================================

THRESHOLD = 18.0

# =====================================================
# Recognition Loop
# =====================================================

while True:

    success, frame = camera.read()

    if not success:
        break

    faces = app.get(frame)

    for face in faces:

        embedding = face.embedding

        best_student = "Unknown"
        best_distance = float("inf")

        for student_id, saved_embeddings in database.items():

            distances = [
                np.linalg.norm(embedding - emb)
                for emb in saved_embeddings
            ]

            minimum_distance = min(distances)

            if minimum_distance < best_distance:
                best_distance = minimum_distance
                best_student = student_id

        if best_distance > THRESHOLD:
            best_student = "Unknown"

        # =====================================================
        # Automatic Attendance
        # =====================================================

        if best_student != "Unknown":

            marked = attendance.mark_attendance(best_student)

            if marked:
                print(f"✅ Attendance Marked : {best_student}")

        # =====================================================

        x1, y1, x2, y2 = face.bbox.astype(int)

        color = (0, 255, 0)

        if best_student == "Unknown":
            color = (0, 0, 255)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            frame,
            best_student,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        cv2.putText(
            frame,
            f"{best_distance:.2f}",
            (x1, y2 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

    cv2.imshow("AI Smart Classroom", frame)

    key = cv2.waitKey(1)

    if key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()