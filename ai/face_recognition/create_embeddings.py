import os
import cv2
import pickle

from insightface.app import FaceAnalysis

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
# Dataset
# =====================================================

DATASET_DIR = "datasets/students"

embeddings = {}

# =====================================================
# Loop Through Students
# =====================================================

for student_id in sorted(os.listdir(DATASET_DIR)):

    student_folder = os.path.join(DATASET_DIR, student_id)

    # Skip files like .gitkeep
    if not os.path.isdir(student_folder):
        continue

    print("\n" + "=" * 70)
    print("Student :", student_id)
    print("=" * 70)

    student_embeddings = []

    image_list = sorted(
        [
            file
            for file in os.listdir(student_folder)
            if file.lower().endswith((".jpg", ".jpeg", ".png"))
        ],
        key=lambda x: int(os.path.splitext(x)[0])
    )

    for image_name in image_list:

        image_path = os.path.join(student_folder, image_name)

        image = cv2.imread(image_path)

        if image is None:
            print(f"Cannot Read : {image_name}")
            continue

        faces = app.get(image)

        if len(faces) == 0:
            print(f"Face Not Found : {image_name}")
            continue

        embedding = faces[0].embedding.copy()

        student_embeddings.append(embedding)

        print(f"Processed : {image_name}")

    if len(student_embeddings) == 0:

        print("No Valid Faces Found.")
        continue

    embeddings[student_id] = student_embeddings

    print(f"Saved {len(student_embeddings)} embeddings.")

# =====================================================
# Save Embeddings
# =====================================================

os.makedirs("embeddings", exist_ok=True)

save_path = "embeddings/face_embeddings.pkl"

with open(save_path, "wb") as file:
    pickle.dump(embeddings, file)

print("\n")
print("=" * 70)
print("Embeddings Saved Successfully")
print("Students :", len(embeddings))
print("Location :", save_path)
print("=" * 70)