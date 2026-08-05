import os
import cv2

# ====================================
# Student Information
# ====================================

STUDENT_ID = "24AD095"

SAVE_DIR = f"datasets/students/{STUDENT_ID}"

os.makedirs(
    SAVE_DIR,
    exist_ok=True,
)

# ====================================
# Load Face Detector
# ====================================

cascade_path = (
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)

face_detector = cv2.CascadeClassifier(
    cascade_path
)

# ====================================
# Open Webcam
# ====================================

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not camera.isOpened():

    print("Unable to open webcam.")

    exit()

image_count = len(os.listdir(SAVE_DIR))

print("=" * 60)
print("AI SMART CLASSROOM")
print("FACE REGISTRATION")
print("=" * 60)
print("S -> Save Face")
print("Q -> Quit")
print("=" * 60)

# ====================================
# Main Loop
# ====================================

while True:

    success, frame = camera.read()

    if not success:
        break

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY,
    )

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.03,
        minNeighbors=5,
        minSize=(40, 40),
    )

    status = "No Face"

    color = (0, 0, 255)

    largest_face = None

    if len(faces) > 0:

        largest_face = max(
            faces,
            key=lambda f: f[2] * f[3]
        )

        x, y, w, h = largest_face

        padding = 25

        x1 = max(0, x - padding)
        y1 = max(0, y - padding)

        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        status = "Face Detected"

        color = (0, 255, 0)

        distance = "Medium"

        if w > 280:

            distance = "Too Close"

        elif w < 120:

            distance = "Too Far"

        cv2.putText(
            frame,
            f"Distance : {distance}",
            (20, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

    cv2.putText(
        frame,
        f"Status : {status}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
    )

    cv2.putText(
        frame,
        f"Saved : {image_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        "S : Save",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2,
    )

    cv2.putText(
        frame,
        "Q : Quit",
        (20, 185),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2,
    )

    cv2.imshow(
        "AI Smart Classroom - Face Registration",
        frame,
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):

        if largest_face is None:

            print("No face detected.")

            continue

        x, y, w, h = largest_face

        padding = 25

        x1 = max(0, x - padding)
        y1 = max(0, y - padding)

        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)

        face = frame[
            y1:y2,
            x1:x2
        ]

        blur_score = cv2.Laplacian(
            cv2.cvtColor(
                face,
                cv2.COLOR_BGR2GRAY
            ),
            cv2.CV_64F,
        ).var()

        if blur_score < 100:

            print("Blurred image. Please keep your face steady.")

            continue

        face = cv2.resize(
            face,
            (224, 224)
        )

        filename = os.path.join(
            SAVE_DIR,
            f"{image_count}.jpg"
        )

        cv2.imwrite(
            filename,
            face
        )

        print(
            f"Saved : {filename}"
        )

        image_count += 1

    elif key == ord("q"):

        break

camera.release()

cv2.destroyAllWindows()