"""Standalone phone detection module based on the active YOLOv8 model.

This module is intentionally independent from the production attention pipeline
so that we can validate phone detection logic safely before a live integration.
"""

from __future__ import annotations

from typing import List, Dict, Any


PHONE_CLASS_ID = 67
PHONE_CLASS_NAME = "cell phone"


def filter_phone_detections(detections, min_confidence=0.75):
    """Keep only phone detections above the provided confidence threshold."""
    if not detections:
        return []

    filtered = []
    for item in detections:
        if item is None:
            continue

        class_id = item.get("class_id")
        class_name = item.get("class_name")
        confidence = float(item.get("confidence", 0.0))

        if class_id == PHONE_CLASS_ID or class_name == PHONE_CLASS_NAME:
            if confidence >= min_confidence:
                filtered.append(item)

    return filtered


def is_phone_usage_detected(phone_detections, min_confidence=0.75):
    """Return True when at least one valid phone detection is found."""
    filtered = filter_phone_detections(phone_detections, min_confidence=min_confidence)
    return len(filtered) > 0


def find_phone_in_person(person_box, phone):
    """Check whether a phone falls inside a person bounding box.

    person_box format: [x1, y1, x2, y2]
    phone format: {"bbox": [x1, y1, x2, y2], ...}
    """
    if person_box is None or phone is None:
        return False

    bbox = phone.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False

    px1, py1, px2, py2 = person_box
    tx1, ty1, tx2, ty2 = bbox

    overlap_x = max(0, min(px2, tx2) - max(px1, tx1))
    overlap_y = max(0, min(py2, ty2) - max(py1, ty1))
    overlap_area = overlap_x * overlap_y

    person_area = max(0.0, (px2 - px1) * (py2 - py1))
    phone_area = max(0.0, (tx2 - tx1) * (ty2 - ty1))
    if person_area <= 0 or phone_area <= 0:
        return False

    return overlap_area / max(phone_area, 1e-6) > 0.10


def detect_phone_objects(model, frame, conf_threshold=0.75, iou_threshold=0.5):
    """Run a YOLO model to detect phone objects on a frame.

    This function is intentionally small and does not touch the production
    pipeline. It works with any Ultralytics model that contains the phone class.
    """
    if model is None or frame is None:
        return []

    results = model(frame, conf=conf_threshold, iou=iou_threshold, verbose=False)
    detections = []

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for idx in range(len(boxes)):
            cls_id = int(boxes.cls[idx].item())
            cls_name = model.names.get(cls_id, "unknown")
            conf = float(boxes.conf[idx].item())
            bbox = boxes.xyxy[idx].cpu().numpy().astype(float).tolist()

            if cls_id == PHONE_CLASS_ID or cls_name == PHONE_CLASS_NAME:
                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": conf,
                    "bbox": bbox,
                })

    return detections


def build_phone_detection_result(phone_detections, min_confidence=0.75):
    """Convert raw phone detections into a consistent result payload."""
    filtered = filter_phone_detections(phone_detections, min_confidence=min_confidence)

    return {
        "phone_detected": len(filtered) > 0,
        "phone_count": len(filtered),
        "phones": filtered,
    }
