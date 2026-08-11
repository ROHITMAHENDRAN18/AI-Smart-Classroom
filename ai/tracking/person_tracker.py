import cv2

from ultralytics import YOLO
import supervision as sv

# ---------------------------------------
# Load YOLO
# ---------------------------------------

print("Loading YOLO...")

model = YOLO("yolov8n.pt")

print("YOLO Loaded.")

# ---------------------------------------
# ByteTrack
# ---------------------------------------

tracker = sv.ByteTrack()

box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

# ---------------------------------------
# Webcam
# ---------------------------------------

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("=" * 60)
print("Person Tracking Started")
print("Press Q to Exit")
print("=" * 60)

while True:

    success, frame = camera.read()

    if not success:
        break

    results = model(frame, verbose=False)[0]

    detections = sv.Detections.from_ultralytics(results)

    detections = detections[detections.class_id == 0]

    detections = tracker.update_with_detections(detections)

    labels = [
        f"ID {track_id}"
        for track_id in detections.tracker_id
    ]

    frame = box_annotator.annotate(
        scene=frame,
        detections=detections
    )

    frame = label_annotator.annotate(
        scene=frame,
        detections=detections,
        labels=labels
    )

    cv2.imshow(
        "ByteTrack Demo",
        frame
    )

    if cv2.waitKey(1) == ord("q"):
        break

camera.release()

cv2.destroyAllWindows()