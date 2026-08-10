import cv2
from insightface.app import FaceAnalysis

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

image = cv2.imread(
    "datasets/students/24AD095/0.jpg"
)

faces = app.get(image)

print("Faces Detected:", len(faces))