"""
Notification model using Flask-SQLAlchemy
"""
import os
import datetime
import threading
import queue
from typing import List, Dict, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func
from config.settings import config

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Thread-safe notification queue for background thread notifications
notification_queue = queue.Queue()
_flask_app = None

class Notification(db.Model):
    """Notification model for SQLAlchemy"""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False, default='info')
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
    
    def to_dict(self) -> Dict:
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def add_notification(cls, title: str, message: str, notification_type: str = 'info') -> Optional['Notification']:
        """Add a new notification to the database"""
        try:
            notification = cls(
                title=title, # type: ignore
                message=message, # type: ignore
                type=notification_type, # type: ignore
                timestamp=datetime.datetime.utcnow() # type: ignore
            )
            
            db.session.add(notification)
            db.session.commit()
            return notification
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to add notification: {e}")
            return None
    
    @classmethod
    def get_recent_notifications(cls, limit: int = 20) -> List[Dict]:
        """Get recent notifications from the database"""
        try:
            notifications = cls.query.order_by(cls.timestamp).limit(limit).all()
            return [notification.to_dict() for notification in notifications]
        except Exception as e:
            print(f"[ERROR] Failed to get notifications: {e}")
            return []
    
    @classmethod
    def get_notifications_by_type(cls, notification_type: str, limit: int = 20) -> List[Dict]:
        """Get notifications filtered by type"""
        try:
            notifications = (cls.query
                           .filter_by(type=notification_type)
                           .order_by(desc(cls.timestamp))
                           .limit(limit)
                           .all())
            return [notification.to_dict() for notification in notifications]
        except Exception as e:
            print(f"[ERROR] Failed to get notifications by type: {e}")
            return []
    
    @classmethod
    def get_notifications_by_date(cls, date: str, limit: int = 50) -> List[Dict]:
        """Get notifications for a specific date (YYYY-MM-DD)"""
        try:
            target_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            notifications = (cls.query
                           .filter(func.date(cls.timestamp) == target_date)
                           .order_by(desc(cls.timestamp))
                           .limit(limit)
                           .all())
            return [notification.to_dict() for notification in notifications]
        except Exception as e:
            print(f"[ERROR] Failed to get notifications by date: {e}")
            return []
    
    @classmethod
    def count_notifications(cls) -> int:
        """Get total count of notifications"""
        try:
            return cls.query.count()
        except Exception as e:
            print(f"[ERROR] Failed to count notifications: {e}")
            return 0
    
    @classmethod
    def clear_all_notifications(cls) -> bool:
        """Clear all notifications from the database"""
        try:
            cls.query.delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to clear notifications: {e}")
            return False
    
    @classmethod
    def clear_old_notifications(cls, days: int = 30) -> int:
        """Clear notifications older than specified days"""
        try:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            deleted_count = cls.query.filter(cls.timestamp < cutoff_date).delete()
            db.session.commit()
            return deleted_count
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to clear old notifications: {e}")
            return 0
    
    @classmethod
    def get_notification_stats(cls) -> Dict:
        """Get notification statistics"""
        try:
            # Total count
            total = cls.query.count()
            
            # Count by type
            type_counts_query = (db.session.query(cls.type, func.count(cls.id))
                               .group_by(cls.type)
                               .all())
            type_counts = {type_name: count for type_name, count in type_counts_query}
            
            # Recent activity (last 24 hours)
            recent_24h_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
            recent_24h = cls.query.filter(cls.timestamp >= recent_24h_cutoff).count()
            
            return {
                'total': total,
                'by_type': type_counts,
                'recent_24h': recent_24h
            }
        except Exception as e:
            print(f"[ERROR] Failed to get notification stats: {e}")
            return {'total': 0, 'by_type': {}, 'recent_24h': 0}


class NotificationManager:
    """Manager class for notification operations"""
    
    @staticmethod
    def init_app(app):
        """Initialize the database with Flask app"""
        global _flask_app
        _flask_app = app
        
        # Initialize database (assumes SQLALCHEMY_DATABASE_URI is already configured in app)
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
        # Start background processor for queued notifications
        NotificationManager._start_background_processor()
    
    @staticmethod
    def _start_background_processor():
        """Start background thread to process queued notifications"""
        def process_notifications():
            while True:
                try:
                    # Get notification from queue (blocking)
                    notification_data = notification_queue.get(timeout=1.0)
                    
                    # Process within Flask app context
                    if _flask_app:
                        with _flask_app.app_context():
                            title, message, notification_type = notification_data
                            Notification.add_notification(title, message, notification_type)
                    
                    notification_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[ERROR] Background notification processing failed: {e}")
        
        processor_thread = threading.Thread(target=process_notifications, daemon=True)
        processor_thread.start()
    
    @staticmethod
    def add_notification(title: str, message: str, notification_type: str = 'info') -> Optional[int]:
        """Add a new notification (must be called within Flask app context)"""
        notification = Notification.add_notification(title, message, notification_type)
        return notification.id if notification else None
    
    @staticmethod
    def add_notification_safe(title: str, message: str, notification_type: str = 'info') -> Optional[int]:
        """Thread-safe method to add notification from any thread"""
        try:
            # If we're in Flask app context, add directly
            if _flask_app and _flask_app.app_context:
                return NotificationManager.add_notification(title, message, notification_type)
        except RuntimeError:
            # Not in app context, queue for background processing
            pass
        
        # Queue for background processing
        try:
            notification_queue.put((title, message, notification_type), timeout=1.0)
            return 1  # Return dummy ID to indicate success
        except queue.Full:
            print(f"[ERROR] Notification queue is full, dropping notification: {title}")
            return None
    
    @staticmethod
    def get_recent_notifications(limit: int = 20) -> List[Dict]:
        """Get recent notifications"""
        return Notification.get_recent_notifications(limit)
    
    @staticmethod
    def clear_all_notifications() -> bool:
        """Clear all notifications"""
        return Notification.clear_all_notifications()
    
    @staticmethod
    def get_notification_stats() -> Dict:
        """Get notification statistics"""
        return Notification.get_notification_stats()


# Global manager instance
notification_manager = NotificationManager()
