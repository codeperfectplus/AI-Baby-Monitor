"""
Camera API Routes - Clean separation between read and write operations
"""
from flask import Blueprint, request, jsonify
from services.controller.camera_service import camera_service, camera_control_service
import logging

# Separate blueprints for read and control operations
camera_info_bp = Blueprint('camera_info', __name__)
camera_control_bp = Blueprint('camera_control', __name__)

logger = logging.getLogger(__name__)


# ==================== READ-ONLY CAMERA INFORMATION ROUTES ====================
@camera_info_bp.route('/api/camera/info', methods=['GET'])
def get_camera_info():
    """Get camera basic information, connection status, and presets."""
    try:
        # Get camera status
        status = camera_service.get_status()
        
        # Get camera presets
        presets = camera_service.get_presets()
        
        return jsonify({
            'success': status['available'],
            'device_model': status['device_model'],
            'privacy_mode': status['privacy_mode'],
            'connection_status': status['connection_status'],
            'presets': presets,
            'error': status.get('error') if not status['available'] else None
        })
    except Exception as e:
        logger.error(f"Error getting camera info: {e}")
        return jsonify({
            'success': False,
            'device_model': 'Error',
            'privacy_mode': False,
            'connection_status': 'error',
            'presets': [],
            'error': str(e)
        }), 500

# ==================== CAMERA CONTROL ROUTES ====================

@camera_control_bp.route('/api/camera/preset/<int:preset_id>', methods=['POST'])
def set_camera_preset(preset_id):
    """Set camera to specific preset position."""
    try:
        if not camera_service.is_available():
            return jsonify({
                'success': False,
                'error': 'Camera is not available'
            }), 400
        
        result = camera_control_service.set_preset(preset_id)
        status_code = 200 if result['success'] else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in set_camera_preset endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@camera_control_bp.route('/api/camera/privacy', methods=['POST'])
def toggle_camera_privacy():
    """Toggle camera privacy mode."""
    try:
        if not camera_service.is_available():
            return jsonify({
                'success': False,
                'error': 'Camera is not available'
            }), 400
        
        data = request.get_json()
        if not data or 'enabled' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing enabled parameter'
            }), 400
        
        enabled = data.get('enabled', False)
        result = camera_control_service.set_privacy_mode(enabled)
        status_code = 200 if result['success'] else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in toggle_camera_privacy endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
