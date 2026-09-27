def main():
    import pickle
    import warnings

    import cv2
    import numpy as np
    from insightface.app import FaceAnalysis

    warnings.filterwarnings("ignore", category=FutureWarning)
    print("Loading InsightFace...")

    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=(640, 640))

    print("Loading image...")
    image = cv2.imread("datasets/students/24AD095/0.jpg")
    if image is None:
        raise FileNotFoundError("Could not read the face test image.")

    faces = app.get(image)
    if not faces:
        raise RuntimeError("No face found in the test image.")

    embedding_from_image = faces[0].embedding
    print("Embedding from image")
    print(type(embedding_from_image))
    print(embedding_from_image.shape)
    print(embedding_from_image[:10])

    with open("embeddings/face_embeddings.pkl", "rb") as file:
        database = pickle.load(file)
    embedding_from_database = database["24AD095"][0]

    print("Embedding from pickle")
    print(type(embedding_from_database))
    print(embedding_from_database.shape)
    print(embedding_from_database[:10])
    print("Distance =", np.linalg.norm(embedding_from_image - embedding_from_database))
    print("Arrays Equal =", np.array_equal(embedding_from_image, embedding_from_database))
    print("All Close =", np.allclose(embedding_from_image, embedding_from_database))


if __name__ == "__main__":
    main()