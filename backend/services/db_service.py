"""
Database Service — SQLite persistence for detection history and alerts.
"""
from __future__ import annotations

import aiosqlite
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.config import DB_PATH

logger = logging.getLogger(__name__)

_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _init_tables(_db)
    return _db


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS detection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bin_id TEXT NOT NULL,
            fill_percentage REAL NOT NULL,
            status TEXT NOT NULL,
            waste_count INTEGER DEFAULT 0,
            waste_inside INTEGER DEFAULT 0,
            waste_outside INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            bin_id TEXT NOT NULL,
            fill_percentage REAL DEFAULT 0,
            resolved INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_history_ts ON detection_history(timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);
    """)
    await db.commit()
    logger.info("Database tables initialized")


async def save_detection(
    bin_id: str,
    fill_percentage: float,
    status: str,
    waste_count: int,
    waste_inside: int,
    waste_outside: int,
):
    db = await get_db()
    await db.execute(
        """INSERT INTO detection_history
           (timestamp, bin_id, fill_percentage, status, waste_count, waste_inside, waste_outside)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), bin_id, fill_percentage, status, waste_count, waste_inside, waste_outside),
    )
    await db.commit()


async def save_alert(
    severity: str,
    message: str,
    bin_id: str,
    fill_percentage: float,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO alerts (timestamp, severity, message, bin_id, fill_percentage)
           VALUES (?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), severity, message, bin_id, fill_percentage),
    )
    await db.commit()
    return cursor.lastrowid


async def resolve_alert(alert_id: int) -> bool:
    db = await get_db()
    cursor = await db.execute("UPDATE alerts SET resolved = 1 WHERE id = ?", (alert_id,))
    await db.commit()
    return cursor.rowcount > 0


async def get_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_detection_history(limit: int = 200) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM detection_history ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_analytics() -> Dict[str, Any]:
    db = await get_db()

    # Total alerts
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM alerts")
    row = await cursor.fetchone()
    total_alerts = row[0] if row else 0

    # Overflow events
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM alerts WHERE severity = 'critical'"
    )
    row = await cursor.fetchone()
    overflow_events = row[0] if row else 0

    # Average fill
    cursor = await db.execute(
        "SELECT AVG(fill_percentage) as avg_fill FROM detection_history"
    )
    row = await cursor.fetchone()
    avg_fill = row[0] if row and row[0] else 0

    # Recent history points
    cursor = await db.execute(
        """SELECT timestamp, fill_percentage, waste_count, status
           FROM detection_history ORDER BY id DESC LIMIT 100"""
    )
    rows = await cursor.fetchall()
    history = [
        {
            "timestamp": r[0],
            "fill_percentage": r[1],
            "waste_count": r[2],
            "status": r[3],
        }
        for r in rows
    ]

    return {
        "history": list(reversed(history)),
        "total_alerts": total_alerts,
        "overflow_events": overflow_events,
        "avg_fill": round(avg_fill, 1),
    }


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
