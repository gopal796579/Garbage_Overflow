"""
Pydantic schemas for API responses.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BinStatusEnum(str, Enum):
    EMPTY = "empty"
    PARTIAL = "partial"
    OVERFLOWING = "overflowing"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"


class DetectionResponse(BaseModel):
    class_name: str
    confidence: float
    bbox: List[int]
    is_waste: bool
    is_bin: bool


class BinStatusResponse(BaseModel):
    bin_id: str = "BIN-001"
    fill_percentage: float = 0.0
    status: BinStatusEnum = BinStatusEnum.UNKNOWN
    waste_count: int = 0
    waste_inside: int = 0
    waste_outside: int = 0
    is_overflow: bool = False
    details: str = ""
    timestamp: str = ""
    detections: List[DetectionResponse] = []


class AlertResponse(BaseModel):
    id: int
    severity: AlertSeverity
    message: str
    bin_id: str
    fill_percentage: float
    timestamp: str
    resolved: bool = False


class AlertCreate(BaseModel):
    severity: AlertSeverity
    message: str
    bin_id: str
    fill_percentage: float


class AnalyticsPoint(BaseModel):
    timestamp: str
    fill_percentage: float
    waste_count: int
    status: str


class AnalyticsResponse(BaseModel):
    history: List[AnalyticsPoint] = []
    total_alerts: int = 0
    overflow_events: int = 0
    avg_fill: float = 0.0


class ConfigUpdate(BaseModel):
    video_source: Optional[str] = None
    confidence_threshold: Optional[float] = None
    overflow_threshold: Optional[float] = None
