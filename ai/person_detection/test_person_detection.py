import cv2

from ai.person_detection.person_detector import PersonDetector


detector = PersonDetector()

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not camera.isOpened():
    print("Cannot Open Camera")
    exit()

print("=" * 60)
print("YOLOv8 Person Detection")
print("Press Q to Exit")
print("=" * 60)

while True:

    success, frame = camera.read()

    if not success:
        break

    frame = cv2.resize(frame, (1280, 720))

    results = detector.detect(frame)

    for result in results:

        for box in result.boxes:

            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Person {confidence:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow("YOLOv8 Person Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()