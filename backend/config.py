"""
Configuration for Smart Garbage Overflow Detection System.
"""
import os

# ── Video Source ──────────────────────────────────────────────
# Options: integer (webcam index), string (RTSP URL or file path)
VIDEO_SOURCE = os.environ.get("VIDEO_SOURCE", "0")

# ── YOLOv8 Model ─────────────────────────────────────────────
MODEL_PATH = os.environ.get("MODEL_PATH", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.45"))
IOU_THRESHOLD = float(os.environ.get("IOU_THRESHOLD", "0.5"))

# Classes from COCO dataset that are relevant for waste/garbage detection
# These serve as demo proxies until a custom model is trained
WASTE_CLASSES = [
    "bottle", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut",
    "cake", "handbag", "backpack", "suitcase", "umbrella",
    "cell phone", "book", "vase", "scissors", "toothbrush",
]

# All COCO classes – bin-like objects for detecting bin regions
BIN_LIKE_CLASSES = ["suitcase", "handbag", "backpack", "bowl", "vase"]

# ── Fill Level Thresholds ────────────────────────────────────
EMPTY_THRESHOLD = 0.30      # 0 – 30% → Empty
PARTIAL_THRESHOLD = 0.80    # 30 – 80% → Partially Filled
# Above 80% → Overflowing

# ── Alert Settings ───────────────────────────────────────────
ALERT_COOLDOWN_SECONDS = 30   # Min seconds between repeat alerts for same bin
OVERFLOW_AREA_RATIO = 0.15    # Garbage outside bin area threshold to trigger overflow

# ── Inference ────────────────────────────────────────────────
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
INFERENCE_SIZE = 640  # YOLOv8 input size
TARGET_FPS = 15       # Target frames per second for streaming

# ── Database ─────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "garbage_detection.db")

# ── Server ───────────────────────────────────────────────────
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
