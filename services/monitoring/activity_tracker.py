"""
User activity tracking service for monitoring who is currently watching
"""
from datetime import datetime, timedelta
from flask_login import current_user
from typing import Dict, List, Optional
import threading

class UserActivityTracker:
    """Track active users and their session information"""
    
    def __init__(self):
        self._active_users = {}  # {user_id: {username, relationship, last_seen, session_id}}
        self._lock = threading.Lock()
    
    def add_active_user(self, user, session_id: str) -> None:
        """Add or update an active user"""
        with self._lock:
            user_id = user.id if user and hasattr(user, 'id') else 'anonymous'
            self._active_users[user_id] = {
                'username': user.username if user and hasattr(user, 'username') else 'Anonymous',
                'relationship': getattr(user, 'relationship', 'Guest') if user else 'Guest',
                'last_seen': datetime.utcnow(),
                'session_id': session_id,
                'is_admin': getattr(user, 'is_admin', False) if user else False
            }
    
    def remove_active_user(self, user_id: str) -> None:
        """Remove a user from active list"""
        with self._lock:
            if user_id in self._active_users:
                del self._active_users[user_id]
    
    def update_last_seen(self, user_id: str) -> None:
        """Update the last seen timestamp for a user"""
        with self._lock:
            if user_id in self._active_users:
                self._active_users[user_id]['last_seen'] = datetime.utcnow()
    
    def get_active_users(self) -> List[Dict]:
        """Get list of currently active users"""
        with self._lock:
            current_time = datetime.utcnow()
            active_threshold = current_time - timedelta(minutes=5)  # 5 minutes timeout
            
            active_users = []
            users_to_remove = []
            
            for user_id, user_data in self._active_users.items():
                if user_data['last_seen'] > active_threshold:
                    active_users.append({
                        'id': user_id,
                        'user_id': user_id,
                        'username': user_data['username'],
                        'relationship': user_data['relationship'],
                        'last_seen': user_data['last_seen'].isoformat(),
                        'is_admin': user_data.get('is_admin', False),
                        'session_id': user_data.get('session_id'),
                        'session_duration': str(current_time - user_data['last_seen']).split('.')[0]
                    })
                else:
                    users_to_remove.append(user_id)
            
            # Clean up inactive users
            for user_id in users_to_remove:
                del self._active_users[user_id]
            
            return sorted(active_users, key=lambda x: x['last_seen'], reverse=True)
    
    def get_active_count(self) -> int:
        """Get count of currently active users"""
        return len(self.get_active_users())
    
    def is_user_active(self, user_id: str) -> bool:
        """Check if a specific user is currently active"""
        active_users = self.get_active_users()
        return any(user['user_id'] == user_id for user in active_users)

# Global instance
activity_tracker = UserActivityTracker()

def get_activity_tracker() -> UserActivityTracker:
    """Get the global activity tracker instance"""
    return activity_tracker
