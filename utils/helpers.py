"""
Utility functions for RTSP Recorder application
"""
import os
import datetime
from collections import deque
try:
    from plyer import notification as plyer_notification
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False
    
from config.settings import config


def get_time_block(hour):
    """Get time block string based on hour"""
    start_hour = (hour // config.TIME_BLOCK_HOURS) * config.TIME_BLOCK_HOURS
    end_hour = start_hour + config.TIME_BLOCK_HOURS
    return f"{start_hour:02d}-{end_hour:02d}"


def get_folder_path():
    """Generate folder path for recordings based on date and time"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    now_hour = datetime.datetime.now().hour
    block = get_time_block(now_hour)
    folder_path = os.path.join(config.MONITOR_RECORDINGS_DIR, today, block)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_filename():
    """Generate filename for recording"""
    folder = get_folder_path()
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    return os.path.join(folder, f"tapo_{timestamp}.avi")


def log_line(msg):
    """Log message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {msg}"
    print(line)
    try:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
        with open(config.LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify(title, message):
    """Send system notification"""
    try:
        if config.NOTIFY_ON_PERSON and NOTIFICATION_AVAILABLE:
            # Check if we're in a Docker/headless environment
            if os.environ.get('DOCKER_CONTAINER') or not os.environ.get('DISPLAY'):
                # Log notification instead of showing GUI notification
                log_line(f"[NOTIFICATION] {title}: {message}")
                return
            
            plyer_notification.notify(title=title, message=message, timeout=5) # type: ignore
    except Exception as e:
        # Just log the notification content instead of showing the error
        log_line(f"[NOTIFICATION] {title}: {message}")
        if config.DEBUG_VIDEO:  # Only show warning in debug mode
            print(f"[DEBUG] Notification system unavailable: {e}")




def get_recent_notifications(limit=10):
    """Get recent notifications for web interface (deprecated - use notification_manager directly)"""
    try:
        from models.notification import notification_manager
        return notification_manager.get_recent_notifications(limit)
    except Exception as e:
        log_line(f"[ERROR] Failed to get recent notifications: {e}")
        return []


def clear_notifications():
    """Clear all notifications (deprecated - use notification_manager directly)"""
    try:
        from models.notification import notification_manager
        return notification_manager.clear_all_notifications()
    except Exception as e:
        log_line(f"[ERROR] Failed to clear notifications: {e}")
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
