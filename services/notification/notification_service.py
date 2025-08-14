"""
Notification service for managing notifications
"""
from models.notification import notification_manager


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


# Global notification service instance
notification_service = NotificationService()

def get_notification_service():
    """Get the global notification service instance"""
    return notification_service
