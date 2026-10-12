from ultralytics import YOLO

from configs.settings import YOLO_MODEL

class PersonDetector:

    def __init__(self, model_path=None):

        print("=" * 60)
        print("Loading YOLOv8 Person Detector...")
        print("=" * 60)

        self.model = YOLO(model_path or YOLO_MODEL)

        print("YOLOv8 Loaded Successfully.")
        print("=" * 60)

    def detect(self, frame):

        results = self.model(

            frame,

            classes=[0],          # Person class only

            conf=0.35,            # Lower confidence

            iou=0.50,             # Better NMS

            imgsz=960,            # Higher image size

            max_det=100,          # Maximum persons

            verbose=False

        )

        return results