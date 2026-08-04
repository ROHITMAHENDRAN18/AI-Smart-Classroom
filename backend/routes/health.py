from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "Healthy",
        "backend": "Running",
        "project": "AI Smart Classroom Attention Monitoring"
    }
@router.get("/test-error")
def test_error():
    raise Exception("This is a test exception")