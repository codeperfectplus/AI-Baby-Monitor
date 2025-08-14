"""
WebSocket event handlers for real-time communication
"""
from flask_socketio import emit
from services.streaming.streaming_service import get_streaming_service
from services.monitoring.monitor_service import get_monitor_service


def register_socketio_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        streaming_service = get_streaming_service()
        
        if streaming_service:
            client_id, client_count = streaming_service.add_client()
            print(f"Client {client_id} connected. Total clients: {client_count}")
            
            # Send initial connection success
            emit('connection_status', {
                'status': 'connected', 
                'client_count': client_count,
                'client_id': client_id
            })
        else:
            emit('connection_status', {
                'status': 'connected', 
                'client_count': 0,
                'client_id': 'offline-mode'
            })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        streaming_service = get_streaming_service()
        
        if streaming_service:
            client_count = streaming_service.remove_client()
            print(f"Client disconnected. Total clients: {client_count}")

    @socketio.on('test_message')
    def handle_test_message(data):
        """Handle test messages for debugging"""
        print(f"Received test message: {data}")
        emit('test_response', {'message': 'Server received: ' + str(data)})

    @socketio.on('request_quality_change')
    def handle_quality_change(data):
        """Handle client request for quality change"""
        streaming_service = get_streaming_service()
        
        if streaming_service:
            quality = data.get('quality', 80)
            new_quality = streaming_service.update_quality(quality)
            emit('quality_changed', {'quality': new_quality})
        else:
            emit('quality_changed', {'quality': 80, 'error': 'Streaming not available'})

    @socketio.on('child_select')
    def handle_child_select(data):
        """Handle child selection via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            x = data.get('x')
            y = data.get('y')
            
            if x is None or y is None:
                emit('child_select_error', {'message': 'Missing coordinates'})
                return
            
            success, message = monitor_service.manual_child_select(x, y)
            
            if success:
                emit('child_select_response', {'success': True, 'message': message})
            else:
                emit('child_select_error', {'message': message})
                
        except Exception as e:
            emit('child_select_error', {'message': str(e)})

    @socketio.on('child_clear')
    def handle_child_clear():
        """Handle clearing child selection via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, message = monitor_service.clear_child_selection()
            
            if success:
                emit('child_clear_response', {'success': True, 'message': message})
            else:
                emit('child_clear_error', {'message': message})
                
        except Exception as e:
            emit('child_clear_error', {'message': str(e)})

    @socketio.on('child_status_request')
    def handle_child_status_request():
        """Handle request for child status via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, data = monitor_service.get_child_status()
            
            if success:
                emit('child_status', data)
            else:
                emit('child_status_error', {'message': data})
                
        except Exception as e:
            emit('child_status_error', {'message': str(e)})

    @socketio.on('toggle_sleep_detection')
    def handle_toggle_sleep_detection():
        """Handle toggling sleep detection via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, data = monitor_service.toggle_sleep_detection()
            
            if success:
                emit('sleep_detection_toggled', {
                    'success': True, 
                    'enabled': data['enabled'], # type: ignore
                    'message': data['message'] # type: ignore
                })
            else:
                emit('sleep_detection_error', {'message': data})
                
        except Exception as e:
            emit('sleep_detection_error', {'message': str(e)})

    @socketio.on('toggle_recording_mode')
    def handle_toggle_recording_mode():
        """Handle toggling between raw/annotated recording mode via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, data = monitor_service.toggle_recording_mode()
            
            if success:
                emit('recording_mode_toggled', {
                    'success': True,
                    'annotated': data['annotated'], # type: ignore
                    'message': data['message'] # type: ignore
                })
            else:
                emit('recording_mode_error', {'message': data})
                
        except Exception as e:
            emit('recording_mode_error', {'message': str(e)})

    @socketio.on('reset_bed_cache')
    def handle_reset_bed_cache():
        """Handle bed cache reset via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, message = monitor_service.reset_bed_cache()
            
            if success:
                emit('bed_cache_reset', {'success': True, 'message': message})
            else:
                emit('bed_cache_error', {'message': message})
                
        except Exception as e:
            emit('bed_cache_error', {'message': str(e)})

    @socketio.on('bed_status_request')
    def handle_bed_status_request():
        """Handle bed status request via WebSocket"""
        monitor_service = get_monitor_service()
        
        try:
            success, data = monitor_service.get_bed_status()
            
            if success:
                emit('bed_status', {
                    'success': True,
                    'bed_cached': data['bed_cached'], # type: ignore
                    'bed_box': data['bed_box'], # type: ignore
                    'frames_confirmed': data['frames_confirmed'], # type: ignore
                    'frames_since_detection': data['frames_since_detection'] # type: ignore
                })
            else:
                emit('bed_status_error', {'message': data})
                
        except Exception as e:
            emit('bed_status_error', {'message': str(e)})

    return socketio
