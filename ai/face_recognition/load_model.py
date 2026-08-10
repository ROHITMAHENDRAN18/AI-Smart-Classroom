from insightface.app import FaceAnalysis

print("=" * 60)
print("Loading InsightFace Model...")
print("=" * 60)

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"],
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640),
)

print()
print("=" * 60)
print("InsightFace Model Loaded Successfully!")
print("=" * 60)