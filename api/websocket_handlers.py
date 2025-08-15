"""
WebSocket event handlers for real-time communication
"""
from flask_socketio import emit
from flask import request
from flask_login import current_user
from services.streaming.streaming_service import get_streaming_service
from services.monitoring.monitor_service import get_monitor_service
from services.monitoring.activity_tracker import get_activity_tracker


def register_socketio_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        from flask_socketio import join_room
        from models.auth import User
        
        streaming_service = get_streaming_service()
        activity_tracker = get_activity_tracker()
        
        # Track active user
        session_id = request.sid
        activity_tracker.add_active_user(current_user, session_id)
        
        # Check if user has streaming permissions and add to appropriate room
        if current_user and current_user.is_authenticated:
            user = User.query.get(current_user.id)
            if user and user.streaming_enabled:
                join_room('streaming_enabled')
                print(f"User {user.username} joined streaming room")
            else:
                print(f"User {user.username if user else 'Unknown'} denied streaming access")
        
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
        
        # Broadcast active users update to all admin users
        socketio.emit('active_users_update', {
            'active_users': activity_tracker.get_active_users(),
            'count': activity_tracker.get_active_count()
        }, room='admin_room')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        streaming_service = get_streaming_service()
        activity_tracker = get_activity_tracker()
        
        # Remove user from active tracking
        user_id = current_user.id if current_user and hasattr(current_user, 'id') else 'anonymous'
        activity_tracker.remove_active_user(user_id)
        
        if streaming_service:
            client_count = streaming_service.remove_client()
            print(f"Client disconnected. Total clients: {client_count}")
        
        # Broadcast active users update to all admin users
        socketio.emit('active_users_update', {
            'active_users': activity_tracker.get_active_users(),
            'count': activity_tracker.get_active_count()
        }, room='admin_room')

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

    @socketio.on('join_admin_room')
    def handle_join_admin_room():
        """Handle admin users joining the admin room for active user updates"""
        if current_user and hasattr(current_user, 'is_admin') and current_user.is_admin:
            from flask_socketio import join_room
            join_room('admin_room')
            
            # Send current active users to the admin
            activity_tracker = get_activity_tracker()
            emit('active_users_update', {
                'active_users': activity_tracker.get_active_users(),
                'count': activity_tracker.get_active_count()
            })

    @socketio.on('request_active_users')
    def handle_request_active_users():
        """Handle request for current active users (admin only)"""
        if current_user and hasattr(current_user, 'is_admin') and current_user.is_admin:
            activity_tracker = get_activity_tracker()
            emit('active_users_update', {
                'active_users': activity_tracker.get_active_users(),
                'count': activity_tracker.get_active_count()
            })

    @socketio.on('heartbeat')
    def handle_heartbeat():
        """Handle heartbeat to keep user active"""
        activity_tracker = get_activity_tracker()
        user_id = current_user.id if current_user and hasattr(current_user, 'id') else 'anonymous'
        activity_tracker.update_last_seen(user_id)

    return socketio


def notify_streaming_change(socketio, user_id, streaming_enabled):
    """Notify specific user about streaming permission change"""
    from services.monitoring.activity_tracker import get_activity_tracker
    from flask_socketio import join_room, leave_room
    
    activity_tracker = get_activity_tracker()
    active_users = activity_tracker.get_active_users()
    
    # Find the user's session and notify them
    for user_info in active_users:
        if user_info.get('id') == user_id:
            session_id = user_info.get('session_id')
            if session_id:
                if streaming_enabled:
                    # Add user to streaming room
                    socketio.server.enter_room(session_id, 'streaming_enabled')
                    print(f"User {user_id} added to streaming room")
                else:
                    # Remove user from streaming room
                    socketio.server.leave_room(session_id, 'streaming_enabled')
                    print(f"User {user_id} removed from streaming room")
                
                socketio.emit('streaming_permission_changed', {
                    'streaming_enabled': streaming_enabled,
                    'message': 'Your streaming permission has been updated by an administrator.'
                }, room=session_id)
                
    # Also broadcast to admin room for real-time updates
    socketio.emit('user_streaming_updated', {
        'user_id': user_id,
        'streaming_enabled': streaming_enabled
    }, room='admin_room')
