"""
Camera Service Layer - Handles camera operations and abstracts camera controller logic
"""
import logging
from typing import Dict, List, Optional, Any
from services.controller.tapo_camera import TapoCameraController
from config.settings import config


class CameraService:
    """Service layer for camera operations with proper separation of concerns."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._controller = None
        self._is_enabled = config.CAMERA_ENABLED
        self._host = config.CAMERA_HOST
        self._username = config.CAMERA_USERNAME
        self._password = config.CAMERA_PASSWORD
    
    def _get_controller(self):
        """Get or create camera controller instance."""
        if not self._is_enabled:
            return None
            
        if self._controller is None:
            try:
                # Ensure we have valid credentials
                if not self._host or not self._username or not self._password:
                    self.logger.error("Camera credentials not properly configured")
                    return None
                    
                self._controller = TapoCameraController(
                    host=self._host,
                    username=self._username,
                    password=self._password,
                    debug=False
                )
                self.logger.info("Camera controller initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize camera controller: {e}")
                return None
        return self._controller
    
    def is_available(self) -> bool:
        """Check if camera service is available."""
        return self._is_enabled and self._get_controller() is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get camera status and basic information."""
        if not self._is_enabled:
            return {
                'available': False,
                'reason': 'disabled',
                'device_model': 'Camera Disabled',
                'privacy_mode': False,
                'connection_status': 'disabled'
            }
        
        controller = self._get_controller()
        if not controller:
            return {
                'available': False,
                'reason': 'offline',
                'device_model': 'Offline',
                'privacy_mode': False,
                'connection_status': 'offline'
            }
        
        try:
            basic_info = controller.get_basic_info()
            privacy_mode = controller.get_privacy_mode()
            
            # Ensure privacy_mode is always a boolean
            if privacy_mode is None:
                privacy_mode = False
            elif not isinstance(privacy_mode, bool):
                # Convert to boolean if it's not already
                privacy_mode = bool(privacy_mode)
            
            # Extract device model from various possible fields
            device_model = 'Unknown'
            if isinstance(basic_info, dict):
                device_model = basic_info.get('device_info').get('basic_info').get('device_alias')
            self.logger.info(f"Camera status: available=True, privacy_mode={privacy_mode}, device_model={device_model}")
            
            return {
                'available': True,
                'reason': 'connected',
                'device_model': device_model,
                'privacy_mode': privacy_mode,
                'connection_status': 'online',
            }
        except Exception as e:
            self.logger.error(f"Error getting camera status: {e}")
            return {
                'available': False,
                'reason': 'error',
                'device_model': 'Error',
                'privacy_mode': False,
                'connection_status': 'error',
                'error': str(e)
            }
    
    def get_presets(self) -> List[Dict[str, Any]]:
        """Get formatted list of camera presets."""
        controller = self._get_controller()
        if not controller:
            # Return default presets when camera is not available
            return [
                {'id': 1, 'name': 'Home Position'},
                {'id': 2, 'name': 'Sleep Area'},
                {'id': 3, 'name': 'Play Area'}
            ]
        
        try:
            presets = controller.get_presets()
            self.logger.debug(f"Raw presets from controller: {presets}")
            
            formatted_presets = []
            if isinstance(presets, list) and len(presets) > 0:
                # Handle the case where presets is a list with objects containing id-name pairs
                for preset_data in presets:
                    if isinstance(preset_data, dict):
                        # Check if it's the format: {"1": "Bed", "2": "Gate", "3": "back"}
                        for preset_id, preset_name in preset_data.items():
                            try:
                                formatted_presets.append({
                                    'id': int(preset_id),
                                    'name': preset_name
                                })
                            except (ValueError, TypeError):
                                # Fallback if preset_id is not a number
                                formatted_presets.append({
                                    'id': preset_id,
                                    'name': preset_name
                                })
                    else:
                        # Handle other formats
                        formatted_presets.append({
                            'id': len(formatted_presets) + 1,
                            'name': f'Preset {len(formatted_presets) + 1}'
                        })
            
            # If no presets were found or parsed, use default presets
            if not formatted_presets:
                formatted_presets = [
                    {'id': 1, 'name': 'Home Position'},
                    {'id': 2, 'name': 'Sleep Area'},
                    {'id': 3, 'name': 'Play Area'}
                ]
            
            return formatted_presets
            
        except Exception as e:
            self.logger.error(f"Error getting presets: {e}")
            # Return default presets on error
            return [
                {'id': 1, 'name': 'Home Position'},
                {'id': 2, 'name': 'Sleep Area'},
                {'id': 3, 'name': 'Play Area'}
            ]


class CameraControlService:
    """Service layer for camera control operations (movements, settings)."""
    
    def __init__(self, camera_service: CameraService):
        self.camera_service = camera_service
        self.logger = logging.getLogger(__name__)
    
    def set_preset(self, preset_id: int) -> Dict[str, Any]:
        """Set camera to specific preset position."""
        controller = self.camera_service._get_controller()
        if not controller:
            return {'success': False, 'error': 'Camera controller not available'}
        
        try:
            success = controller.set_preset(preset_id)
            if success:
                return {
                    'success': True,
                    'message': f'Camera moved to preset {preset_id}',
                    'preset_id': preset_id
                }
            else:
                return {'success': False, 'error': 'Failed to set camera preset'}
        except Exception as e:
            self.logger.error(f"Error setting camera preset: {e}")
            return {'success': False, 'error': str(e)}
    
    def set_privacy_mode(self, enabled: bool) -> Dict[str, Any]:
        """Toggle camera privacy mode."""
        controller = self.camera_service._get_controller()
        if not controller:
            return {'success': False, 'error': 'Camera controller not available'}
        
        try:
            success = controller.set_privacy_mode(enabled)
            if success:
                return {
                    'success': True,
                    'privacy_mode': enabled,
                    'message': f'Privacy mode {"enabled" if enabled else "disabled"}'
                }
            else:
                return {'success': False, 'error': 'Failed to toggle privacy mode'}
        except Exception as e:
            self.logger.error(f"Error toggling privacy mode: {e}")
            return {'success': False, 'error': str(e)}


# Global service instances
camera_service = CameraService()
camera_control_service = CameraControlService(camera_service)
