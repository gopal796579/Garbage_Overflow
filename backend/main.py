"""
Smart Garbage Overflow Detection System — FastAPI Backend.

Provides:
  - WebSocket /ws/video  → live annotated MJPEG stream
  - WebSocket /ws/status → real-time bin status JSON
  - REST API for alerts, analytics, config
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Set

# Add parent dir to path so 'backend' package resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.config import (
    VIDEO_SOURCE,
    MODEL_PATH,
    HOST,
    PORT,
    FRONTEND_DIR,
    TARGET_FPS,
)
from backend.detector.yolo_detector import YOLODetector
from backend.detector.fill_analyzer import FillAnalyzer
from backend.services.video_service import VideoService
from backend.services.alert_service import AlertService
from backend.services import db_service

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("garbage_detector")

# ── Global State ──────────────────────────────────────────────
detector: YOLODetector | None = None
analyzer: FillAnalyzer | None = None
video_svc: VideoService | None = None
alert_svc: AlertService | None = None

video_ws_clients: Set[WebSocket] = set()
status_ws_clients: Set[WebSocket] = set()

detection_loop_task: asyncio.Task | None = None
_running = False
_latest_status: dict = {}
_save_counter = 0


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global detector, analyzer, video_svc, alert_svc, detection_loop_task, _running

    logger.info("═══ Starting Smart Garbage Overflow Detection System ═══")

    # Initialize components
    detector = YOLODetector(MODEL_PATH)
    analyzer = FillAnalyzer()
    video_svc = VideoService()
    alert_svc = AlertService()

    # Initialize database
    await db_service.get_db()

    # Open video source
    source = VIDEO_SOURCE
    if not video_svc.open(source):
        logger.warning("Could not open video source '%s'. The system will run without live video.", source)

    # Start detection loop
    _running = True
    detection_loop_task = asyncio.create_task(_detection_loop())

    logger.info("═══ System ready — Dashboard at http://localhost:%d ═══", PORT)

    yield

    # Shutdown
    _running = False
    if detection_loop_task:
        detection_loop_task.cancel()
    video_svc.close()
    await db_service.close_db()
    logger.info("═══ System shut down ═══")


app = FastAPI(
    title="Smart Garbage Overflow Detection",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Detection Loop ────────────────────────────────────────────
async def _detection_loop():
    """Background loop: capture → detect → analyze → broadcast."""
    global _latest_status, _save_counter

    logger.info("Detection loop started")

    while _running:
        try:
            if video_svc is None or not video_svc.is_opened:
                await asyncio.sleep(1)
                continue

            # Read frame in executor to avoid blocking event loop
            frame = await asyncio.get_event_loop().run_in_executor(
                None, video_svc.read_frame
            )
            if frame is None:
                await asyncio.sleep(0.1)
                continue

            # Run detection in executor
            detections = await asyncio.get_event_loop().run_in_executor(
                None, detector.detect, frame
            )

            # Analyze fill level
            h, w = frame.shape[:2]
            analysis = analyzer.analyze(detections, w, h)

            # Annotate frame
            annotated = await asyncio.get_event_loop().run_in_executor(
                None, video_svc.annotate_frame, frame, detections, analysis
            )

            # Encode to JPEG
            jpeg_bytes = video_svc.encode_frame_jpeg(annotated)

            # Build status payload
            status = analysis.to_dict()
            status["timestamp"] = datetime.now().isoformat()
            status["detections"] = [d.to_dict() for d in detections if d.is_waste or d.is_bin]
            _latest_status = status

            # Broadcast video frame to WebSocket clients
            if video_ws_clients:
                frame_b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                frame_msg = json.dumps({"type": "frame", "data": frame_b64})
                await _broadcast(video_ws_clients, frame_msg)

            # Broadcast status
            if status_ws_clients:
                status_msg = json.dumps({"type": "status", "data": status})
                await _broadcast(status_ws_clients, status_msg)

            # Check for alerts
            alert = await alert_svc.check_and_alert(analysis)
            if alert:
                alert_msg = json.dumps({"type": "alert", "data": alert})
                await _broadcast(status_ws_clients, alert_msg)

            # Save to DB periodically (every 30th frame ~ every 2 seconds)
            _save_counter += 1
            if _save_counter % 30 == 0:
                await db_service.save_detection(
                    bin_id=analysis.bin_id,
                    fill_percentage=round(analysis.fill_percentage * 100, 1),
                    status=analysis.status.value,
                    waste_count=analysis.waste_count,
                    waste_inside=analysis.waste_inside,
                    waste_outside=analysis.waste_outside,
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Detection loop error: %s", e, exc_info=True)
            await asyncio.sleep(1)

    logger.info("Detection loop stopped")


async def _broadcast(clients: Set[WebSocket], message: str):
    """Send message to all connected WebSocket clients."""
    disconnected = set()
    for ws in clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    clients -= disconnected


# ── WebSocket Endpoints ───────────────────────────────────────
@app.websocket("/ws/video")
async def ws_video(websocket: WebSocket):
    await websocket.accept()
    video_ws_clients.add(websocket)
    logger.info("Video client connected (%d total)", len(video_ws_clients))
    try:
        while True:
            # Keep connection alive, listen for control messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        video_ws_clients.discard(websocket)
        logger.info("Video client disconnected (%d total)", len(video_ws_clients))


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await websocket.accept()
    status_ws_clients.add(websocket)
    logger.info("Status client connected (%d total)", len(status_ws_clients))
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        status_ws_clients.discard(websocket)
        logger.info("Status client disconnected (%d total)", len(status_ws_clients))


# ── REST Endpoints ────────────────────────────────────────────
@app.get("/api/bins")
async def get_bins():
    """Current status of all monitored bins."""
    return {"bins": [_latest_status] if _latest_status else []}


@app.get("/api/alerts")
async def get_alerts():
    """Get alert history."""
    alerts = await db_service.get_alerts()
    return {"alerts": alerts}


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved."""
    await db_service.resolve_alert(alert_id)
    return {"status": "resolved", "alert_id": alert_id}


@app.get("/api/analytics")
async def get_analytics():
    """Get analytics data."""
    data = await db_service.get_analytics()
    return data


@app.get("/api/health")
async def health():
    return {
        "status": "running",
        "model": MODEL_PATH,
        "video_source": VIDEO_SOURCE,
        "video_active": video_svc.is_opened if video_svc else False,
        "connected_clients": {
            "video": len(video_ws_clients),
            "status": len(status_ws_clients),
        },
    }


# ── Serve Frontend ────────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Smart Garbage Overflow Detection</h1><p>Frontend not found.</p>")


# Mount static files
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
