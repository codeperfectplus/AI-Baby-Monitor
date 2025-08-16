"""
Configuration settings for RTSP Recorder application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BabyMonitorSettings:
    """Main configuration class for RTSP Recorder"""

    # ==================== RTSP Settings ====================
    RTSP_URL = os.getenv("RTSP_URL") 
    RTSP_TIMEOUT = int(os.getenv("RTSP_TIMEOUT", 10))
    YOLO_MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n.pt")
    
    BASE_DIR = "/app/baby-monitor" if os.path.exists("/app/baby-monitor") \
        else os.path.join(os.path.expanduser("~"), "baby-monitor")

    YOLO_MODEL_PATH = os.path.join(BASE_DIR, "cache", YOLO_MODEL_NAME)
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "database.db")
    LOG_FILE = os.path.join(BASE_DIR, "logs", "detections.log")
    MONITOR_RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
    SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")

    SEGMENT_MINUTES = 30  # length of each video file in minutes
    TIME_BLOCK_HOURS = 6  # how to split day into folders
    SHOW_PREVIEW = True  # True = show live preview, False = headless
    SAVE_ANNOTATED = True  # True = save video with boxes
    
    # ==================== AI Model Settings ====================
    # Use Docker-compatible paths if running in container
    
    CONFIDENCE_THRESHOLD = 0.4  # detection confidence
    TARGET_FPS = 30.0  # reduced fps for CPU processing
    DEBUG_VIDEO = True  # enable extra video debugging output
    
    # GPU usage flag
    USE_GPU = False
    GPU_DEVICE_INDEX = int(os.getenv("GPU_DEVICE_INDEX", 0))  # which GPU to use
    
    # ==================== Logging Settings ====================
    # Use Docker-compatible paths if running in container
    
    NOTIFY_ON_PERSON = True  # OS notification for person/child alert
    
    # ==================== Tracking Settings ====================
    MANUAL_CHILD_SELECT = False  # click on the child once to lock on their track id
    AUTO_SELECT_SMALLEST = True  # if not manually selected, pick smallest person bbox
    
    # ==================== Safety Settings ====================
    USE_BED_SAFE_ZONE = True
    SAFE_MARGIN_RATIO = 0.15  # 15% inside bed rect is "safe"
    RISK_FRAMES_THRESHOLD = 10  # consecutive frames outside safe zone before alert
    ALERT_COOLDOWN_SEC = 20  # suppress repeated alerts within this period
    
    # ==================== Sleep Detection Settings ====================
    SLEEP_DETECTION_ENABLED = True  # Enable sleep/wake monitoring
    MOVEMENT_THRESHOLD = 30  # pixels - minimum movement to consider as "moving"
    SLEEP_TIME_SEC = 150  # 2.5 minutes of no movement = sleep (150 seconds)
    WAKE_NOTIFICATION_COOLDOWN = 60  # seconds between wake notifications
    
    # ==================== DeepSORT Settings ====================
    MAX_AGE = 30
    N_INIT = 3
    MAX_COSINE_DISTANCE = 0.2
    NN_BUDGET = 100
    
    # ==================== RTSP Reader Settings ====================
    MAX_RETRIES = 5
    RETRY_DELAY = 3
    MAX_FAILURES = 30  # consecutive failures before reconnecting

    # tracker settings
    CHILD_HISTORY_SIZE = 30
    CHILD_MIN_HISTORY = 5
    CHILD_HEIGHT_RATIO_THRESHOLD = 0.50
    CHILD_STABILITY_FRAMES = 3

    LOG_LEVEL = "INFO"


# Create global config instance
config = BabyMonitorSettings()
