import numpy as np

from ai.phone_detection.phone_detector import (
    build_phone_detection_result,
    filter_phone_detections,
    find_phone_in_person,
    is_phone_usage_detected,
)


def make_phone_result(x1=10, y1=20, x2=60, y2=70, conf=0.90):
    return {
        "bbox": [x1, y1, x2, y2],
        "confidence": conf,
        "class_id": 67,
        "class_name": "cell phone",
    }


def test_filter_phone_detections_keeps_only_phone_class():
    detections = [
        make_phone_result(conf=0.92),
        {"bbox": [0, 0, 20, 20], "confidence": 0.50, "class_id": 0, "class_name": "person"},
        {"bbox": [70, 70, 100, 100], "confidence": 0.80, "class_id": 67, "class_name": "cell phone"},
    ]

    filtered = filter_phone_detections(detections, min_confidence=0.75)
    assert len(filtered) == 2
    assert all(item["class_name"] == "cell phone" for item in filtered)


def test_find_phone_in_person_association():
    person_box = [0, 0, 200, 200]
    phone = make_phone_result(30, 40, 90, 100)

    assert find_phone_in_person(person_box, phone) is True


def test_is_phone_usage_detected_has_threshold_behavior():
    assert is_phone_usage_detected([make_phone_result(conf=0.86)], min_confidence=0.75) is True
    assert is_phone_usage_detected([make_phone_result(conf=0.40)], min_confidence=0.75) is False


def test_build_phone_detection_result_returns_expected_shape():
    result = build_phone_detection_result([make_phone_result()])
    assert result["phone_count"] == 1
    assert result["phones"][0]["class_name"] == "cell phone"
    assert result["phone_detected"] is True
    assert result["phones"][0]["confidence"] >= 0.0
