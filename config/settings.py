"""
Configuration settings for RTSP Recorder application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Main configuration class for RTSP Recorder"""

    # ==================== RTSP Settings ====================
    RTSP_URL = os.getenv("RTSP_URL") 
    # ==================== Recording Settings ====================
    # Use Docker-compatible paths if running in container, otherwise use home directory
    MONITOR_RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", 
                                      "/app/data/recordings" if os.path.exists("/app/data") 
                                      else os.path.join(os.path.expanduser("~"), "baby-monitor/recordings"))
    SNAPSHOTS_DIR = os.getenv("SNAPSHOTS_DIR",
                             "/app/data/snapshots" if os.path.exists("/app/data") 
                             else os.path.join(os.path.expanduser("~"), "baby-monitor/snapshots"))
    SEGMENT_MINUTES = 30  # length of each video file in minutes
    TIME_BLOCK_HOURS = 6  # how to split day into folders
    SHOW_PREVIEW = True  # True = show live preview, False = headless
    SAVE_ANNOTATED = True  # True = save video with boxes; False = save raw frames
    
    # ==================== AI Model Settings ====================
    # Use Docker-compatible paths if running in container
    YOLO_MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n.pt")
    YOLO_MODEL_PATH = os.getenv("MODEL_PATH",
                          os.path.join("/app/data/cache", YOLO_MODEL_NAME) if os.path.exists("/app/data")
                          else os.path.join(os.path.expanduser("~"), "baby-monitor/cache", YOLO_MODEL_NAME))
    CONFIDENCE_THRESHOLD = 0.4  # detection confidence
    TARGET_FPS = 30.0  # reduced fps for CPU processing
    DEBUG_VIDEO = True  # enable extra video debugging output
    
    # ==================== Logging Settings ====================
    # Use Docker-compatible paths if running in container
    LOG_FILE = os.getenv("LOG_FILE",
                        os.path.join("/app/data/logs", "detections.log") if os.path.exists("/app/data")
                        else os.path.join(os.path.expanduser("~"), "baby-monitor/logs", "detections.log"))
    NOTIFY_ON_PERSON = True  # OS notification for person/child alert
    
    # ==================== Tracking Settings ====================
    MANUAL_CHILD_SELECT = True  # click on the child once to lock on their track id
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


# Create global config instance
config = Config()
