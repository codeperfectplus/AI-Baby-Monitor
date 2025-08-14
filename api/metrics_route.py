"""
Metrics API routes for system and streaming metrics
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from services.streaming.streaming_service import get_streaming_service

metrics_bp = Blueprint('metrics', __name__)


@metrics_bp.route('/metrics')
@login_required
def get_metrics():
    """Get system and streaming metrics"""
    streaming_service = get_streaming_service()
    if streaming_service:
        metrics = streaming_service.get_metrics()
        return jsonify(metrics)
    else:
        # Return basic metrics when streaming is not available
        import psutil
        return jsonify({
            'cpu': psutil.cpu_percent(interval=0.1),
            'memory': psutil.virtual_memory().percent,
            'network': 0,
            'detection_rate': 0,
            'sleep_state': 'Offline',
            'room_temp': 24,
            'sleep_time': '0m',
            'streaming': {
                'active_clients': 0,
                'adaptive_fps': 0,
                'adaptive_quality': 0
            }
        })
