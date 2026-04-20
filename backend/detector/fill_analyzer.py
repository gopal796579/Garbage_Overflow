"""
Fill-Level Analyzer — estimates bin fill percentage and status.

Strategy:
  1. If a bin-like object is detected, use it as the region of interest (ROI).
  2. Count waste objects inside vs outside the bin region.
  3. Calculate fill percentage based on area coverage ratio.
  4. If no bin is detected, use the lower 60% of the frame as a virtual bin ROI
     (simulating a camera pointed at a bin).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from backend.config import (
    EMPTY_THRESHOLD,
    PARTIAL_THRESHOLD,
    OVERFLOW_AREA_RATIO,
)
from backend.detector.yolo_detector import Detection

logger = logging.getLogger(__name__)


class BinStatus(str, Enum):
    EMPTY = "empty"
    PARTIAL = "partial"
    OVERFLOWING = "overflowing"
    UNKNOWN = "unknown"


@dataclass
class FillAnalysis:
    """Result of a single fill-level analysis."""
    bin_id: str = "BIN-001"
    fill_percentage: float = 0.0
    status: BinStatus = BinStatus.UNKNOWN
    waste_count: int = 0
    waste_inside: int = 0
    waste_outside: int = 0
    bin_bbox: Optional[Tuple[int, int, int, int]] = None
    is_overflow: bool = False
    details: str = ""

    def to_dict(self):
        return {
            "bin_id": self.bin_id,
            "fill_percentage": round(self.fill_percentage * 100, 1),
            "status": self.status.value,
            "waste_count": self.waste_count,
            "waste_inside": self.waste_inside,
            "waste_outside": self.waste_outside,
            "bin_bbox": list(self.bin_bbox) if self.bin_bbox else None,
            "is_overflow": self.is_overflow,
            "details": self.details,
        }


class FillAnalyzer:
    """Analyzes fill level of a bin based on YOLO detections."""

    def __init__(
        self,
        empty_threshold: float = EMPTY_THRESHOLD,
        partial_threshold: float = PARTIAL_THRESHOLD,
        overflow_area_ratio: float = OVERFLOW_AREA_RATIO,
    ):
        self.empty_threshold = empty_threshold
        self.partial_threshold = partial_threshold
        self.overflow_area_ratio = overflow_area_ratio

    def analyze(
        self,
        detections: List[Detection],
        frame_width: int,
        frame_height: int,
    ) -> FillAnalysis:
        """
        Analyze detections to determine bin fill level.
        """
        waste_items = [d for d in detections if d.is_waste]
        bin_items = [d for d in detections if d.is_bin]

        # Determine the bin region
        if bin_items:
            # Use the largest bin-like detection as the bin ROI
            bin_det = max(bin_items, key=lambda d: d.area)
            bin_bbox = bin_det.bbox
        else:
            # Virtual bin: lower 60% of frame, center 80%
            margin_x = int(frame_width * 0.1)
            top_y = int(frame_height * 0.4)
            bin_bbox = (margin_x, top_y, frame_width - margin_x, frame_height)

        analysis = FillAnalysis(bin_bbox=bin_bbox)
        analysis.waste_count = len(waste_items)

        if not waste_items:
            analysis.fill_percentage = 0.0
            analysis.status = BinStatus.EMPTY
            analysis.details = "No waste detected"
            return analysis

        # Classify waste as inside or outside bin
        bx1, by1, bx2, by2 = bin_bbox
        bin_area = max((bx2 - bx1) * (by2 - by1), 1)

        inside_area = 0
        outside_area = 0
        inside_count = 0
        outside_count = 0

        for w in waste_items:
            wx1, wy1, wx2, wy2 = w.bbox
            # Calculate overlap with bin region
            overlap_x1 = max(bx1, wx1)
            overlap_y1 = max(by1, wy1)
            overlap_x2 = min(bx2, wx2)
            overlap_y2 = min(by2, wy2)

            if overlap_x1 < overlap_x2 and overlap_y1 < overlap_y2:
                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
            else:
                overlap_area = 0

            # If > 50% of waste object is inside bin → classify as inside
            if w.area > 0 and overlap_area / w.area > 0.5:
                inside_area += w.area
                inside_count += 1
            else:
                outside_area += w.area
                outside_count += 1

        analysis.waste_inside = inside_count
        analysis.waste_outside = outside_count

        # Fill percentage = ratio of waste area inside bin to total bin area
        # Capped at 1.0, with a density multiplier for multiple objects
        density_factor = min(1.0 + (inside_count - 1) * 0.15, 2.0) if inside_count > 0 else 1.0
        raw_fill = (inside_area / bin_area) * density_factor
        analysis.fill_percentage = min(raw_fill, 1.0)

        # Check for overflow: garbage detected outside bin
        outside_ratio = outside_area / bin_area if bin_area > 0 else 0
        is_outside_overflow = outside_ratio > self.overflow_area_ratio

        # Classify status
        if analysis.fill_percentage >= self.partial_threshold or is_outside_overflow:
            analysis.status = BinStatus.OVERFLOWING
            analysis.is_overflow = True
            if is_outside_overflow:
                analysis.details = f"Overflow: {outside_count} item(s) outside bin region"
            else:
                analysis.details = f"Overflow: fill level at {analysis.fill_percentage*100:.0f}%"
        elif analysis.fill_percentage >= self.empty_threshold:
            analysis.status = BinStatus.PARTIAL
            analysis.details = f"Partially filled: {analysis.fill_percentage*100:.0f}%"
        else:
            analysis.status = BinStatus.EMPTY
            analysis.details = f"Low fill: {analysis.fill_percentage*100:.0f}%"

        return analysis
