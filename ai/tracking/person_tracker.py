import cv2
from ultralytics import YOLO
import supervision as sv


class PersonTracker:

    def __init__(self):

        print("=" * 60)
        print("Loading YOLOv8 Person Detector...")
        print("=" * 60)

        self.model = YOLO("yolov8m.pt")

        print("YOLOv8 Loaded Successfully.")

        # ---------------------------------------
        # ByteTrack
        # ---------------------------------------

        print("Initializing ByteTrack...")

        self.tracker = sv.ByteTrack()

        print("ByteTrack Initialized Successfully.")

        # ---------------------------------------
        # Annotators
        # ---------------------------------------

        self.box_annotator = sv.BoxAnnotator()

        self.label_annotator = sv.LabelAnnotator()

        print("=" * 60)

    # ---------------------------------------
    # Detect + Track
    # ---------------------------------------

    def track(self, frame):

        # ---------------------------------------
        # YOLO Person Detection
        # ---------------------------------------

        results = self.model(
            frame,
            classes=[0],
            conf=0.35,
            iou=0.50,
            imgsz=960,
            max_det=100,
            verbose=False
        )[0]

        # ---------------------------------------
        # Convert YOLO results
        # to Supervision detections
        # ---------------------------------------

        detections = sv.Detections.from_ultralytics(
            results
        )

        # ---------------------------------------
        # ByteTrack
        # ---------------------------------------

        detections = self.tracker.update_with_detections(
            detections
        )

        return detections

    # ---------------------------------------
    # Draw Tracking Results
    # ---------------------------------------

    def annotate(self, frame, detections):

        labels = []

        if detections.tracker_id is not None:

            for track_id in detections.tracker_id:

                labels.append(
                    f"Person ID {track_id}"
                )

        frame = self.box_annotator.annotate(
            scene=frame,
            detections=detections
        )

        frame = self.label_annotator.annotate(
            scene=frame,
            detections=detections,
            labels=labels
        )

        return frame


# =====================================================
# Standalone Test
# =====================================================

if __name__ == "__main__":

    print("=" * 60)
    print("ByteTrack Person Tracking Test")
    print("Press Q to Exit")
    print("=" * 60)

    tracker = PersonTracker()

    camera = cv2.VideoCapture(0)

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

    while True:

        success, frame = camera.read()

        if not success:

            print("❌ Failed to Read Frame")

            break

        # ---------------------------------------
        # Tracking
        # ---------------------------------------

        detections = tracker.track(frame)

        # ---------------------------------------
        # Draw results
        # ---------------------------------------

        frame = tracker.annotate(
            frame,
            detections
        )

        # ---------------------------------------
        # Display number of tracked persons
        # ---------------------------------------

        person_count = len(detections)

        cv2.putText(
            frame,
            f"Tracked Persons: {person_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        # ---------------------------------------
        # Display
        # ---------------------------------------

        cv2.imshow(
            "AI Smart Classroom - ByteTrack",
            frame
        )

        # ---------------------------------------
        # Exit
        # ---------------------------------------

        if cv2.waitKey(1) & 0xFF == ord("q"):

            break

    camera.release()

    cv2.destroyAllWindows()

    print("Tracking Stopped.")