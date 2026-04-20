"""
Alert Service — manages overflow alerts with cooldown logic.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, Optional

from backend.config import ALERT_COOLDOWN_SECONDS
from backend.detector.fill_analyzer import FillAnalysis, BinStatus
from backend.services import db_service

logger = logging.getLogger(__name__)


class AlertService:
    """Generates and manages alerts for bin overflow events."""

    def __init__(self, cooldown_seconds: int = ALERT_COOLDOWN_SECONDS):
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_time: Dict[str, float] = {}
        self._active_alerts: Dict[str, int] = {}  # bin_id → alert_id

    async def check_and_alert(self, analysis: FillAnalysis) -> Optional[Dict]:
        """
        Check if an alert should be generated based on fill analysis.
        Returns alert dict if a new alert was created, None otherwise.
        """
        bin_id = analysis.bin_id
        now = time.time()

        # Check cooldown
        last_time = self._last_alert_time.get(bin_id, 0)
        if now - last_time < self.cooldown_seconds:
            return None

        if analysis.is_overflow:
            severity = "critical"
            message = f"🚨 OVERFLOW DETECTED — {analysis.details}"
        elif analysis.status == BinStatus.PARTIAL and analysis.fill_percentage > 0.65:
            severity = "warning"
            message = f"⚠️ Bin nearing capacity — {analysis.fill_percentage*100:.0f}% full"
        else:
            # No alert needed — resolve any active alert
            if bin_id in self._active_alerts:
                await db_service.resolve_alert(self._active_alerts[bin_id])
                del self._active_alerts[bin_id]
            return None

        # Create alert
        alert_id = await db_service.save_alert(
            severity=severity,
            message=message,
            bin_id=bin_id,
            fill_percentage=analysis.fill_percentage * 100,
        )

        self._last_alert_time[bin_id] = now
        self._active_alerts[bin_id] = alert_id

        alert_data = {
            "id": alert_id,
            "severity": severity,
            "message": message,
            "bin_id": bin_id,
            "fill_percentage": round(analysis.fill_percentage * 100, 1),
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
        }

        logger.warning("Alert generated: %s", message)
        return alert_data
