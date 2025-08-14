"""
Monitor API routes for child tracking, sleep detection, and bed monitoring
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.monitoring.monitor_service import get_monitor_service

monitor_bp = Blueprint('monitor', __name__)


@monitor_bp.route('/child/clear', methods=['POST'])
@login_required
def clear_child_selection():
    """Clear child selection"""
    monitor_service = get_monitor_service()
    success, message = monitor_service.clear_child_selection()
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 503


@monitor_bp.route('/child/select', methods=['POST'])
@login_required
def manual_child_select():
    """Manually select child by coordinates"""
    monitor_service = get_monitor_service()
    
    try:
        data = request.get_json()
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({'success': False, 'message': 'Missing x or y coordinates'}), 400
        
        success, message = monitor_service.manual_child_select(x, y)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 503
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Invalid request data: {str(e)}'}), 400


@monitor_bp.route('/child/status')
@login_required
def get_child_status():
    """Get current child selection status"""
    monitor_service = get_monitor_service()
    success, data = monitor_service.get_child_status()
    
    if success:
        return jsonify(data)
    else:
        return jsonify({'success': False, 'message': data}), 503


@monitor_bp.route('/sleep/toggle', methods=['POST'])
@login_required
def toggle_sleep_detection():
    """Toggle sleep detection on/off"""
    monitor_service = get_monitor_service()
    success, data = monitor_service.toggle_sleep_detection()
    
    if success:
        return jsonify({
            'success': True,
            'enabled': data['enabled'], # type: ignore
            'message': data['message'] # type: ignore
        })
    else:
        return jsonify({'success': False, 'message': data}), 503


@monitor_bp.route('/recording/toggle', methods=['POST'])
@login_required
def toggle_recording_mode():
    """Toggle between raw and annotated recording mode"""
    monitor_service = get_monitor_service()
    success, data = monitor_service.toggle_recording_mode()
    
    if success:
        return jsonify({
            'success': True,
            'annotated': data['annotated'], # type: ignore
            'message': data['message'] # type: ignore
        })
    else:
        return jsonify({'success': False, 'message': data}), 503


@monitor_bp.route('/bed/reset', methods=['POST'])
@login_required
def reset_bed_cache():
    """Reset cached bed detection"""
    monitor_service = get_monitor_service()
    success, message = monitor_service.reset_bed_cache()
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 503


@monitor_bp.route('/bed/status')
@login_required
def get_bed_status():
    """Get current bed detection status"""
    monitor_service = get_monitor_service()
    success, data = monitor_service.get_bed_status()
    
    if success:
        return jsonify({
            'success': True,
            'bed_cached': data['bed_cached'], # type: ignore
            'bed_box': data['bed_box'], # type: ignore
            'frames_confirmed': data['frames_confirmed'], # type: ignore
            'frames_since_detection': data['frames_since_detection'] # type: ignore
        })
    else:
        return jsonify({'success': False, 'message': data}), 503


@monitor_bp.route('/snapshot', methods=['POST'])
@login_required
def take_snapshot():
    """Take a snapshot of the current frame"""
    monitor_service = get_monitor_service()
    success, data = monitor_service.take_snapshot()
    
    if success:
        return jsonify({
            'success': True, 
            'message': data['message'],  # type: ignore
            'path': data['path'] # type: ignore
        })
    else:
        if 'No frame available' in data:
            return jsonify({'success': False, 'message': data}), 400
        else:
            return jsonify({'success': False, 'message': data}), 503
