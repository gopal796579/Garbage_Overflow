"""
YOLOv8n Detector — wraps the Ultralytics model for garbage detection.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

import numpy as np

from ultralytics import YOLO

from backend.config import (
    MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    IOU_THRESHOLD,
    WASTE_CLASSES,
    BIN_LIKE_CLASSES,
    INFERENCE_SIZE,
)

logger = logging.getLogger(__name__)


class Detection:
    """Single detected object."""

    __slots__ = ("class_name", "confidence", "bbox", "area", "is_waste", "is_bin")

    def __init__(
        self,
        class_name: str,
        confidence: float,
        bbox: tuple[int, int, int, int],
    ):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2)
        x1, y1, x2, y2 = bbox
        self.area = (x2 - x1) * (y2 - y1)
        self.is_waste = class_name in WASTE_CLASSES
        self.is_bin = class_name in BIN_LIKE_CLASSES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "area": self.area,
            "is_waste": self.is_waste,
            "is_bin": self.is_bin,
        }


class YOLODetector:
    """Loads YOLOv8n and runs inference on frames."""

    def __init__(self, model_path: str = MODEL_PATH):
        logger.info("Loading YOLOv8 model from %s …", model_path)
        self.model = YOLO(model_path)
        # Build class name → index lookup from model
        self.class_names: Dict[int, str] = self.model.names
        logger.info("Model loaded — %d classes available", len(self.class_names))

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run inference on a single BGR frame.
        Returns list of Detection objects.
        """
        results = self.model.predict(
            source=frame,
            imgsz=INFERENCE_SIZE,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            verbose=False,
        )

        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                class_name = self.class_names.get(cls_id, f"class_{cls_id}")
                detections.append(
                    Detection(
                        class_name=class_name,
                        confidence=conf,
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                    )
                )

        return detections

    def get_waste_detections(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to only waste-related objects."""
        return [d for d in detections if d.is_waste]

    def get_bin_detections(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to only bin-like objects."""
        return [d for d in detections if d.is_bin]
