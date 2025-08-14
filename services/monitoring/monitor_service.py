"""
Monitor services for child tracking, sleep detection, and bed monitoring
"""
from services.streaming.streaming_service import get_streaming_service


class MonitorService:
    """Service for managing child monitoring, sleep detection, and bed detection"""
    
    def __init__(self):
        pass
    
    def clear_child_selection(self):
        """Clear child selection"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            streaming_service.ai_streamer.tracker.clear_child_selection()
            return True, 'Child selection cleared successfully'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def manual_child_select(self, x, y):
        """Manually select child by coordinates"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                # Set click point for manual selection
                streaming_service.ai_streamer.tracker.set_click_point((int(x), int(y)))
                return True, f'Child selection attempted at ({x}, {y})'
            except Exception as e:
                return False, f'Failed to select child: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def get_child_status(self):
        """Get current child selection status"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                child_id = streaming_service.ai_streamer.tracker.child_id
                if child_id is not None:
                    return True, {
                        'selected': True,
                        'child_id': child_id,
                        'confidence': streaming_service.ai_streamer.tracker.track_confidences.get(child_id, 0),
                        'class': streaming_service.ai_streamer.tracker.track_classes.get(child_id, 'unknown')
                    }
                else:
                    return True, {'selected': False, 'child_id': None}
            except Exception as e:
                return False, f'Failed to get child status: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def toggle_sleep_detection(self):
        """Toggle sleep detection on/off"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                streaming_service.ai_streamer.sleep_monitor.enabled = not streaming_service.ai_streamer.sleep_monitor.enabled
                status = "enabled" if streaming_service.ai_streamer.sleep_monitor.enabled else "disabled"
                return True, {
                    'enabled': streaming_service.ai_streamer.sleep_monitor.enabled,
                    'message': f'Sleep detection {status}'
                }
            except Exception as e:
                return False, f'Failed to toggle sleep detection: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def toggle_recording_mode(self):
        """Toggle between raw and annotated recording mode"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                streaming_service.ai_streamer.save_annotated = not streaming_service.ai_streamer.save_annotated
                mode = "annotated" if streaming_service.ai_streamer.save_annotated else "raw"
                return True, {
                    'annotated': streaming_service.ai_streamer.save_annotated,
                    'message': f'Recording mode switched to {mode}'
                }
            except Exception as e:
                return False, f'Failed to toggle recording mode: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def reset_bed_cache(self):
        """Reset cached bed detection"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                streaming_service.ai_streamer.detector.reset_bed_cache()
                return True, 'Bed cache reset - will re-detect bed location'
            except Exception as e:
                return False, f'Failed to reset bed cache: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def get_bed_status(self):
        """Get current bed detection status"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            try:
                status = streaming_service.ai_streamer.detector.get_bed_status()
                return True, {
                    'bed_cached': status['cached'],
                    'bed_box': status['bed_box'],
                    'frames_confirmed': status['frames_confirmed'],
                    'frames_since_detection': status['frames_since_detection']
                }
            except Exception as e:
                return False, f'Failed to get bed status: {str(e)}'
        return False, 'Streaming system not available (running in auth-only mode)'
    
    def take_snapshot(self):
        """Take a snapshot of the current frame"""
        streaming_service = get_streaming_service()
        if streaming_service and streaming_service.ai_streamer:
            from config.settings import config
            
            frame = streaming_service.ai_streamer.get_latest_frame()
            if frame is not None:
                try:
                    snapshot_path = streaming_service.ai_streamer.recorder.save_snapshot(frame, config.SNAPSHOTS_DIR)
                    return True, {'message': 'Snapshot saved successfully', 'path': snapshot_path}
                except Exception as e:
                    return False, f'Failed to save snapshot: {str(e)}'
            else:
                return False, 'No frame available for snapshot'
        return False, 'Streaming system not available (running in auth-only mode)'


# Global monitor service instance
monitor_service = MonitorService()

def get_monitor_service():
    """Get the global monitor service instance"""
    return monitor_service
