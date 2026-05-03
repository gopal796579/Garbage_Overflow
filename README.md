# 🗑️ Smart Garbage Overflow Detection System

AI-powered real-time waste bin monitoring using **YOLOv8n** with a premium dark-mode dashboard.

![Dashboard](frontend/assets/screenshot.png)

## ✨ Features

- **Real-Time Detection** — YOLOv8n processes live video feed to detect garbage and waste objects
- **Fill-Level Classification** — Bins classified as Empty (🟢), Partially Filled (🟡), or Overflowing (🔴)
- **Overflow Detection** — Triggers when fill exceeds 80% or garbage detected outside bin region
- **Live Dashboard** — Premium glassmorphism UI with animated gauges, charts, and alerts
- **Alert System** — Real-time notifications with sound alerts for critical overflow events
- **Analytics** — Historical fill-level trends, alert frequency, and waste count tracking
- **Database Persistence** — SQLite stores detection history and alert logs

## 🏗️ Architecture

```
┌─────────────────┐       WebSocket       ┌──────────────────────┐
│  Web Dashboard   │◄────────────────────►│   FastAPI Backend     │
│  (HTML/CSS/JS)   │   /ws/video, /ws/status│                      │
│                  │                       │  ┌─ YOLOv8n Detector │
│  • Live Video    │   REST API            │  ├─ Fill Analyzer    │
│  • Fill Gauge    │◄────────────────────►│  ├─ Video Service    │
│  • Alerts        │   /api/alerts, etc.   │  ├─ Alert Service    │
│  • Analytics     │                       │  └─ DB Service       │
└─────────────────┘                       └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the System

```bash
# From project root
python -m backend.main
```

The dashboard will be available at **http://localhost:8000**

### 3. Configure Video Source

Set the video source via environment variable:

```bash
# Webcam (default)
set VIDEO_SOURCE=0

# RTSP camera
set VIDEO_SOURCE=rtsp://192.168.1.100:554/stream

# Video file
set VIDEO_SOURCE=path/to/video.mp4
```

### 4. Optional API Security (recommended)

Protect write endpoints and restrict allowed browser origins:

```bash
# Comma-separated list of frontend origins allowed by CORS
set ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# If set, clients must send X-API-Key for write endpoints
set API_WRITE_KEY=change-me
```

## 📊 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/ws/video` | WebSocket | Live annotated video stream |
| `/ws/status` | WebSocket | Real-time bin status updates |
| `/api/bins` | GET | Current bin status |
| `/api/alerts` | GET | Alert history |
| `/api/alerts/{id}/resolve` | POST | Resolve an alert |
| `/api/analytics` | GET | Analytics data |
| `/api/health` | GET | System health check |

## 🎯 Training Custom Model

To train YOLOv8n on your own waste detection dataset:

### 1. Download Dataset from Roboflow

```bash
python -m backend.training.train download \
    --api-key YOUR_API_KEY \
    --workspace YOUR_WORKSPACE \
    --project waste-bin-detection \
    --version 1
```

### 2. Train

```bash
python -m backend.training.train train \
    --dataset path/to/data.yaml \
    --epochs 100 \
    --batch 16
```

### 3. Use Custom Model

```bash
set MODEL_PATH=runs/detect/garbage_detector/weights/best.pt
python -m backend.main
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | YOLOv8n (Ultralytics) |
| Backend | Python, FastAPI, OpenCV |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Database | SQLite (aiosqlite) |
| Streaming | WebSockets |

## 📝 License

MIT License — free for educational and commercial use.
