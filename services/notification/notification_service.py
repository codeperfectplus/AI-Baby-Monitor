"""
Notification service for managing notifications
"""
from models.notification import notification_manager
from config.settings import config
from utils.helpers import log_line

class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        self.notification_manager = notification_manager
    
    def get_recent_notifications(self, limit=20):
        """Get recent notifications for the web interface"""
        try:
            notifications = self.notification_manager.get_recent_notifications(limit=limit)
            return True, notifications
        except Exception as e:
            return False, f'Failed to get notifications: {str(e)}'
    
    def clear_all_notifications(self):
        """Clear all notifications"""
        try:
            success = self.notification_manager.clear_all_notifications()
            message = 'All notifications cleared' if success else 'Failed to clear notifications'
            return success, message
        except Exception as e:
            return False, f'Failed to clear notifications: {str(e)}'
    
    def add_notification(self, message, notification_type='info'):
        """Add a new notification"""
        try:
            self.notification_manager.add_notification(message, notification_type)
            return True, 'Notification added successfully'
        except Exception as e:
            return False, f'Failed to add notification: {str(e)}'


    def dispatch_notification(self, title, message):
        """Send notification to web interface using SQLAlchemy"""
        try:
            if config.NOTIFY_ON_PERSON:
                notification_type = self.get_notification_type(title)
                notification_id = notification_manager.add_notification_safe(title, message, notification_type)
                
                if notification_id:
                    log_line(f"[WEB_NOTIFICATION] {title}: {message}")
                else:
                    log_line(f"[ERROR] Failed to save web notification: {title}: {message}")
                
        except Exception as e:
            log_line(f"[ERROR] Web notification failed: {e}")

    def get_notification_type(self, title):
        """Determine notification type based on title for UI styling"""
        title_lower = title.lower()
        if 'wake' in title_lower or 'awake' in title_lower:
            return 'info'
        elif 'sleep' in title_lower:
            return 'success'
        elif 'warning' in title_lower or 'fall' in title_lower or 'risk' in title_lower:
            return 'warning'
        elif 'alert' in title_lower or 'danger' in title_lower:
            return 'error'
        else:
            return 'info'

# Global notification service instance
notification_service = NotificationService()

def get_notification_service():
    """Get the global notification service instance"""
    return notification_service
