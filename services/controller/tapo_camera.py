import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from pytapo import Tapo


class TapoCameraController:
    """
    A comprehensive controller for TP-Link Tapo cameras with extensive functionality.
    """
    
    def __init__(self, host: str, username: str, password: str, debug: bool = False):
        """
        Initialize the Tapo camera controller.
        
        Args:
            host (str): Camera IP address
            username (str): Tapo account username/email
            password (str): Tapo account password
            debug (bool): Enable debug logging
        """
        self.host = host
        self.username = username
        self.password = password
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        try:
            self.camera = Tapo(host, username, password)
            self.logger.info(f"Successfully connected to camera at {host}")
        except Exception as e:
            self.logger.error(f"Failed to connect to camera: {e}")
            raise
    
    def get_basic_info(self) -> Dict:
        """Get basic camera information."""
        try:
            info = self.camera.getBasicInfo()
            # Ensure we return a dict even if the API returns something else
            return info if isinstance(info, dict) else {"data": info}
        except Exception as e:
            self.logger.error(f"Failed to get basic info: {e}")
            return {}
    
    def set_privacy_mode(self, enabled: bool) -> bool:
        """
        Enable or disable privacy mode.
        
        Args:
            enabled (bool): True to enable privacy mode, False to disable
            
        Returns:
            bool: Success status
        """
        try:
            self.camera.setPrivacyMode(enabled)
            status = "enabled" if enabled else "disabled"
            self.logger.info(f"Privacy mode {status}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set privacy mode: {e}")
            return False
    
    def get_privacy_mode(self) -> Optional[bool]:
        """Get current privacy mode status."""
        try:
            status = self.camera.getPrivacyMode()
            self.logger.info(f"Raw privacy mode status: {status}")
            
            # Handle different response formats
            if isinstance(status, dict):
                enabled_value = status.get('enabled', 'off')
                # Convert string values to boolean
                if isinstance(enabled_value, str):
                    return enabled_value.lower() in ['on', 'true', '1', 'enabled']
                elif isinstance(enabled_value, bool):
                    return enabled_value
                elif isinstance(enabled_value, int):
                    return bool(enabled_value)
            elif isinstance(status, bool):
                return status
            elif isinstance(status, str):
                return status.lower() in ['on', 'true', '1', 'enabled']
            elif isinstance(status, int):
                return bool(status)
            
            # Default to False if we can't parse it
            self.logger.warning(f"Unknown privacy mode format: {type(status)} - {status}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to get privacy mode status: {e}")
            return None
    
    def set_preset(self, preset_id: int) -> bool:
        """
        Set camera to a preset position.
        
        Args:
            preset_id (int): Preset position ID
            
        Returns:
            bool: Success status
        """
        try:
            self.camera.setPreset(preset_id)
            self.logger.info(f"Set camera to preset {preset_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set preset {preset_id}: {e}")
            return False
    
    def get_presets(self) -> List[Dict]:
        """Get list of available presets."""
        try:
            presets = self.camera.getPresets()
            self.logger.info(f"Retrieved presets")
            # Handle different return types
            if isinstance(presets, list):
                return presets
            elif isinstance(presets, dict):
                return [presets]
            else:
                return [{"data": presets}]
        except Exception as e:
            self.logger.error(f"Failed to get presets: {e}")
            return []
    
    def trigger_alarm(self, duration: int = 10) -> bool:
        try:
            # setAlarm typically takes (enabled, soundEnabled) parameters
            self.camera.setAlarm(True, True)
            self.logger.info(f"Triggered alarm")
            return True
        except Exception as e:
            self.logger.error(f"Failed to trigger alarm: {e}")
            return False
        
    def reboot_camera(self) -> bool:
        """Reboot the camera."""
        try:
            self.camera.reboot()
            self.logger.info("Camera reboot initiated")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reboot camera: {e}")
            return False
