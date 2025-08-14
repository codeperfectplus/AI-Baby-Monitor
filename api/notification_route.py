"""
Notification API routes
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from services.notification.notification_service import get_notification_service

notification_bp = Blueprint('notifications', __name__)


@notification_bp.route('/notifications')
@login_required
def get_notifications():
    """Get recent notifications for the web interface"""
    notification_service = get_notification_service()
    success, data = notification_service.get_recent_notifications(limit=20)
    
    if success:
        return jsonify({'notifications': data})
    else:
        return jsonify({'success': False, 'message': data, 'notifications': []}), 500


@notification_bp.route('/notifications/clear', methods=['POST'])
@login_required
def clear_all_notifications():
    """Clear all notifications"""
    notification_service = get_notification_service()
    success, message = notification_service.clear_all_notifications()
    
    return jsonify({'success': success, 'message': message})
