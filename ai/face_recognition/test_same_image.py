import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
import pickle
import numpy as np
from insightface.app import FaceAnalysis

print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640,640)
)

print("Loading image...")

image = cv2.imread("datasets/students/24AD095/0.jpg")

faces = app.get(image)

print("Faces detected:", len(faces))

embedding1 = faces[0].embedding

print("Embedding from image")
print(type(embedding1))
print(embedding1.shape)
print(embedding1[:10])

print()

database = pickle.load(
    open("embeddings/face_embeddings.pkl","rb")
)

embedding2 = database["24AD095"][0]

print("Embedding from pickle")
print(type(embedding2))
print(embedding2.shape)
print(embedding2[:10])

print()

print("Distance =", np.linalg.norm(embedding1 - embedding2))

print()

print("Arrays Equal =", np.array_equal(embedding1, embedding2))

print()

print("All Close =", np.allclose(embedding1, embedding2))