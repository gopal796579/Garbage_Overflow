"""
Video Service — manages video capture, frame processing, and annotation.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.config import FRAME_WIDTH, FRAME_HEIGHT, TARGET_FPS
from backend.detector.yolo_detector import Detection
from backend.detector.fill_analyzer import FillAnalysis, BinStatus

logger = logging.getLogger(__name__)

# Color scheme for annotations (BGR format)
COLORS = {
    "waste": (0, 200, 255),      # Amber
    "bin": (255, 200, 0),        # Cyan/Teal
    "overflow": (0, 0, 255),     # Red
    "empty": (0, 220, 100),      # Green
    "partial": (0, 200, 255),    # Amber
    "text_bg": (30, 30, 30),     # Dark background
    "roi": (200, 200, 200),      # Gray
}


class VideoService:
    """Manages video capture and frame annotation."""

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self._source = None
        self._frame_count = 0
        self._last_frame_time = 0

    def open(self, source) -> bool:
        """Open a video source. Source can be int (webcam) or str (URL/file)."""
        self.close()

        # Try to parse as integer for webcam index
        try:
            source = int(source)
        except (ValueError, TypeError):
            pass

        logger.info("Opening video source: %s", source)
        self.cap = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            logger.error("Failed to open video source: %s", source)
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self._source = source
        self._frame_count = 0
        logger.info("Video source opened successfully")
        return True

    def read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame. Returns None if source is closed."""
        if self.cap is None or not self.cap.isOpened():
            return None

        # Rate limiting
        now = time.time()
        elapsed = now - self._last_frame_time
        target_interval = 1.0 / TARGET_FPS
        if elapsed < target_interval:
            time.sleep(target_interval - elapsed)

        ret, frame = self.cap.read()
        if not ret:
            # Loop video files
            if isinstance(self._source, str):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return None
            else:
                return None

        self._last_frame_time = time.time()
        self._frame_count += 1

        # Resize for consistency
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        return frame

    def annotate_frame(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        analysis: FillAnalysis,
    ) -> np.ndarray:
        """Draw bounding boxes, labels, and status overlay on frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw bin ROI
        if analysis.bin_bbox:
            bx1, by1, bx2, by2 = analysis.bin_bbox
            roi_color = COLORS["roi"]
            cv2.rectangle(annotated, (bx1, by1), (bx2, by2), roi_color, 2, cv2.LINE_AA)
            cv2.putText(
                annotated, "BIN REGION", (bx1 + 5, by1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, roi_color, 1, cv2.LINE_AA
            )

        # Draw detections
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            if det.is_waste:
                color = COLORS["overflow"] if analysis.is_overflow else COLORS["waste"]
            elif det.is_bin:
                color = COLORS["bin"]
            else:
                continue  # Skip non-relevant detections

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

            # Label
            label = f"{det.class_name} {det.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
            cv2.putText(
                annotated, label, (x1 + 3, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
            )

        # ── Status Overlay (top-left) ──
        self._draw_status_overlay(annotated, analysis)

        # ── Fill Bar (right side) ──
        self._draw_fill_bar(annotated, analysis)

        return annotated

    def _draw_status_overlay(self, frame: np.ndarray, analysis: FillAnalysis):
        """Draw status badge on top-left of frame."""
        status_text = analysis.status.value.upper()
        fill_text = f"Fill: {analysis.fill_percentage*100:.0f}%"
        count_text = f"Waste: {analysis.waste_count} items"

        if analysis.status == BinStatus.OVERFLOWING:
            badge_color = COLORS["overflow"]
        elif analysis.status == BinStatus.PARTIAL:
            badge_color = COLORS["partial"]
        else:
            badge_color = COLORS["empty"]

        # Background
        cv2.rectangle(frame, (8, 8), (220, 90), COLORS["text_bg"], -1)
        cv2.rectangle(frame, (8, 8), (220, 90), badge_color, 2, cv2.LINE_AA)

        # Status
        cv2.putText(frame, status_text, (16, 32),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.65, badge_color, 2, cv2.LINE_AA)
        cv2.putText(frame, fill_text, (16, 55),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
        cv2.putText(frame, count_text, (16, 78),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

    def _draw_fill_bar(self, frame: np.ndarray, analysis: FillAnalysis):
        """Draw vertical fill bar on right side of frame."""
        h, w = frame.shape[:2]
        bar_x = w - 35
        bar_top = 20
        bar_bottom = h - 20
        bar_height = bar_bottom - bar_top

        # Background bar
        cv2.rectangle(frame, (bar_x, bar_top), (bar_x + 20, bar_bottom),
                       COLORS["text_bg"], -1)
        cv2.rectangle(frame, (bar_x, bar_top), (bar_x + 20, bar_bottom),
                       (100, 100, 100), 1, cv2.LINE_AA)

        # Fill level
        fill_h = int(bar_height * min(analysis.fill_percentage, 1.0))
        fill_top = bar_bottom - fill_h

        if analysis.fill_percentage >= 0.8:
            fill_color = COLORS["overflow"]
        elif analysis.fill_percentage >= 0.3:
            fill_color = COLORS["partial"]
        else:
            fill_color = COLORS["empty"]

        if fill_h > 0:
            cv2.rectangle(frame, (bar_x + 2, fill_top), (bar_x + 18, bar_bottom - 2),
                           fill_color, -1)

        # Percentage label
        pct = f"{analysis.fill_percentage*100:.0f}%"
        cv2.putText(frame, pct, (bar_x - 10, bar_top - 5),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1, cv2.LINE_AA)

    def encode_frame_jpeg(self, frame: np.ndarray, quality: int = 75) -> bytes:
        """Encode frame as JPEG bytes."""
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, buffer = cv2.imencode(".jpg", frame, params)
        return buffer.tobytes()

    def close(self):
        """Release video capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Video source closed")

    @property
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
