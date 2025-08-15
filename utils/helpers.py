"""
Utility functions for RTSP Recorder application
"""
import os
import datetime
import logging
from logging.handlers import RotatingFileHandler

from config.settings import config

# --- Logging Setup -----------------------------------------------------------
_logger = None

def _init_logger():
    """Initialize and return the application logger (idempotent)."""
    global _logger
    if _logger:
        return _logger

    logger = logging.getLogger("ai_baby_monitor")
    # Avoid adding handlers multiple times
    if logger.handlers:
        _logger = logger
        return logger

    # Determine level
    level_name = getattr(config, "LOG_LEVEL")
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    # Ensure log directory exists
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler
    max_bytes = getattr(config, "LOG_MAX_BYTES", 2_000_000)  # 2MB default
    backup_count = getattr(config, "LOG_BACKUP_COUNT", 5)
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # capture everything to file
    logger.addHandler(file_handler)

    # Console handler in debug mode
    if getattr(config, "DEBUG_VIDEO", False):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(level)
        logger.addHandler(console)

    _logger = logger
    return logger


def get_logger():
    """Public accessor for the module logger."""
    return _init_logger()


def set_log_level(level: str):
    """Dynamically change log level at runtime."""
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


# Backwards-compatible logging helper
# NOTE: Kept original signature so existing imports keep working.
def log_line(msg: str, level: str = "INFO"):
    """Log a line with timestamp & level (backwards compatible).
    Usage: log_line("Something happened", "WARNING")
    """
    logger = get_logger()
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, msg)


# Convenience wrappers
def log_debug(msg: str):
    log_line(msg, "DEBUG")

def log_info(msg: str):
    log_line(msg, "INFO")

def log_warning(msg: str):
    log_line(msg, "WARNING")

def log_error(msg: str):
    log_line(msg, "ERROR")

def log_exception(msg: str):
    logger = get_logger()
    logger.exception(msg)

# Initialize logger immediately so early imports are covered
_init_logger()

def get_folder_path():
    """Generate folder path for recordings based on date and time"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    folder_path = os.path.join(config.MONITOR_RECORDINGS_DIR, today)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_filename():
    """Generate filename for recording"""
    folder = get_folder_path()
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    return os.path.join(folder, f"tapo_{timestamp}.avi")


def notify(title, message):
    """Send system notification"""
    try:
        if config.NOTIFY_ON_PERSON:
            # Check if we're in a Docker/headless environment
            if os.environ.get('DOCKER_CONTAINER') or not os.environ.get('DISPLAY'):
                # Log notification instead of showing GUI notification
                log_info(f"[NOTIFICATION] {title}: {message}")
                return
            try:
                from plyer import notification as plyer_notification  # type: ignore
                plyer_notification.notify(title=title, message=message, timeout=5)  # type: ignore
            except Exception:
                log_warning(f"[NOTIFICATION-FALLBACK] {title}: {message}")
    except Exception as e:
        # Just log the notification content instead of showing the error
        log_error(f"[NOTIFICATION] {title}: {message}")
        if getattr(config, "DEBUG_VIDEO", False):
            log_debug(f"Notification system unavailable: {e}")


def get_recent_notifications(limit=10):
    """Get recent notifications for web interface (deprecated - use notification_manager directly)"""
    try:
        from models.notification import notification_manager
        return notification_manager.get_recent_notifications(limit)
    except Exception as e:
        log_error(f"[ERROR] Failed to get recent notifications: {e}")
        return []


def clear_notifications():
    """Clear all notifications (deprecated - use notification_manager directly)"""
    try:
        from models.notification import notification_manager
        return notification_manager.clear_all_notifications()
    except Exception as e:
        log_error(f"[ERROR] Failed to clear notifications: {e}")
        return False


def calculate_iou(rect1, rect2):
    """Calculate Intersection over Union (IoU) for two rectangles"""
    x1_1, y1_1, x2_1, y2_1 = rect1
    x1_2, y1_2, x2_2, y2_2 = rect2
    
    # Calculate intersection
    inter_x1 = max(x1_1, x1_2)
    inter_y1 = max(y1_1, y1_2)
    inter_x2 = min(x2_1, x2_2)
    inter_y2 = min(y2_1, y2_2)
    
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    
    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = max(1, area1 + area2 - inter_area)
    
    return inter_area / union_area


def setup_environment():
    """Setup environment variables for optimal performance"""
    # Force CPU-only processing
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    os.environ['YOLO_VERBOSE'] = 'False'
    
    # Force FFmpeg settings for better RTSP performance
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;udp|buffer_size;10240|max_delay;1000000|fflags;nobuffer|threads;1|stimeout;5000000"
    )
    os.environ["OPENCV_VIDEOIO_DEBUG"] = "1"
    os.environ["OPENCV_FFMPEG_WRITER_OPTIONS"] = "threads;1"
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    log_debug("Environment variables set up successfully.")
