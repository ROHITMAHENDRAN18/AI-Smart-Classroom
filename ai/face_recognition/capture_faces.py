import os
import cv2

# ============================================
# Student Information
# ============================================

STUDENT_ID = "24AD095"

SAVE_DIR = f"datasets/students/{STUDENT_ID}"

os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================
# Haar Cascade
# ============================================

cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

face_detector = cv2.CascadeClassifier(cascade_path)

# ============================================
# Webcam
# ============================================

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not camera.isOpened():
    print("Cannot open webcam.")
    exit()

print("=" * 60)
print("AI Smart Classroom - Face Registration")
print("=" * 60)
print("S → Save")
print("Q → Quit")
print("=" * 60)

image_count = 0

while True:

    success, frame = camera.read()

    if not success:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    cv2.putText(
        frame,
        f"Images Saved : {image_count}",
        (20,40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0,255,0),
        2
    )

    largest_face = None

    if len(faces) > 0:

        largest_face = max(
            faces,
            key=lambda f: f[2]*f[3]
        )

        x,y,w,h = largest_face

        padding = int(max(w,h)*0.40)

        x1 = max(0, x-padding)
        y1 = max(0, y-padding)

        x2 = min(frame.shape[1], x+w+padding)
        y2 = min(frame.shape[0], y+h+padding)

        cv2.rectangle(
            frame,
            (x1,y1),
            (x2,y2),
            (0,255,0),
            2
        )

    cv2.imshow(
        "Face Registration",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):

        if largest_face is None:
            print("No face detected.")
            continue

        face = frame[
            y1:y2,
            x1:x2
        ]

        filename = os.path.join(
            SAVE_DIR,
            f"{image_count}.jpg"
        )

        cv2.imwrite(
            filename,
            face
        )

        print("Saved :", filename)

        image_count += 1

    elif key == ord("q"):
        break

camera.release()

cv2.destroyAllWindows()