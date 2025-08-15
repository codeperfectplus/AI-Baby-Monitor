"""
Active users API endpoint for admin monitoring
"""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from services.monitoring.activity_tracker import get_activity_tracker

active_users_bp = Blueprint('active_users', __name__)

def admin_required(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@active_users_bp.route('/active-users')
@login_required
@admin_required
def get_active_users():
    """Get currently active users (admin only)"""
    try:
        activity_tracker = get_activity_tracker()
        active_users = activity_tracker.get_active_users()
        
        return jsonify({
            'success': True,
            'active_users': active_users,
            'count': len(active_users)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
