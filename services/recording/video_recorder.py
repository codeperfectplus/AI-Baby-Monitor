"""
Video recording module for saving footage
"""
import cv2
import os
import time
import numpy as np
from config.settings import config
from utils.helpers import get_filename


class VideoRecorder:
    """Video recording manager with automatic file rotation"""
    
    def __init__(self, fps, frame_size):
        """Initialize video recorder"""
        self.fps = fps
        self.frame_size = frame_size
        self.filename = get_filename()
        self.out = self._make_writer(self.filename, fps, frame_size)
        self.last_save_time = time.time()
        self.paused = False
        
        print(f"[RECORDING] Recording started: {self.filename}")
    
    def _make_writer(self, path, fps, size):
        """Create video writer with fallback codecs"""
        if config.DEBUG_VIDEO:
            print(f"[VIDEO] Creating video writer for: {path}")
            print(f"[VIDEO] Video properties: {size[0]}x{size[1]} @ {fps}fps")
        
        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Failed to create directory {dir_path}: {e}")
        
        # Try MJPG first (best compatibility and quality)
        try:
            fourcc = cv2.VideoWriter.fourcc(*'MJPG')  # type: ignore
            writer = cv2.VideoWriter(path, fourcc, float(fps), size, True)
            
            if writer and writer.isOpened():
                if config.DEBUG_VIDEO:
                    print(f"[VIDEO] Successfully created MJPG writer")
                return writer
            else:
                if writer is not None:
                    writer.release()
        except Exception as e:
            if config.DEBUG_VIDEO:
                print(f"[WARNING] MJPG failed: {e}")
        
        # Fallback to XVID if MJPG fails
        try:
            fourcc = cv2.VideoWriter.fourcc(*'XVID')  # type: ignore
            writer = cv2.VideoWriter(path, fourcc, float(fps), size, True)
            
            if writer and writer.isOpened():
                if config.DEBUG_VIDEO:
                    print(f"[VIDEO] Successfully created XVID writer (fallback)")
                return writer
            else:
                if writer is not None:
                    writer.release()
        except Exception as e:
            if config.DEBUG_VIDEO:
                print(f"[WARNING] XVID failed: {e}")
        
        raise RuntimeError(f"Failed to create VideoWriter for {path}. "
                          f"Neither MJPG nor XVID codecs work on your system.")
    
    def _close_writer_safely(self, writer, filepath):
        """Safely close video writer and validate the output file"""
        if writer is not None:
            try:
                writer.release()
                # Small delay to ensure file is fully written
                time.sleep(0.1)
                
                # Check if file exists and has reasonable size
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > 1000:  # At least 1KB
                        if config.DEBUG_VIDEO:
                            print(f"[VIDEO] Successfully saved: {filepath} ({file_size:,} bytes)")
                        return True
                    else:
                        print(f"[WARNING] Video file too small: {filepath} ({file_size} bytes)")
                        return False
                else:
                    print(f"[ERROR] Video file not found: {filepath}")
                    return False
            except Exception as e:
                print(f"[ERROR] Failed to close video writer: {e}")
                return False
        return False
    
    def write_frame(self, frame):
        """Write a frame to the video file"""
        if self.paused:
            return
            
        frame_to_save = frame
        
        # Ensure frame is the correct size and format
        if frame_to_save.shape[:2] != (self.frame_size[1], self.frame_size[0]):
            frame_to_save = cv2.resize(frame_to_save, self.frame_size)
        
        try:
            # Ensure frame is in correct format (BGR, uint8)
            if frame_to_save.dtype != np.uint8:
                frame_to_save = frame_to_save.astype(np.uint8)
            
            self.out.write(frame_to_save)
            
        except Exception as e:
            print(f"[ERROR] Failed to write frame: {e}")
            # Try to recreate the writer
            try:
                self._close_writer_safely(self.out, self.filename)
                self.out = self._make_writer(self.filename, self.fps, self.frame_size)
                print("[VIDEO] Video writer recreated after exception")
                self.out.write(frame_to_save)  # Retry writing the frame
            except Exception as e2:
                print(f"[ERROR] Failed to recreate video writer: {e2}")
    
    def check_rotation(self):
        """Check if file rotation is needed"""
        if time.time() - self.last_save_time >= config.SEGMENT_MINUTES * 60:
            self.rotate_file()
    
    def rotate_file(self):
        """Rotate to a new video file"""
        # Properly close current file
        self._close_writer_safely(self.out, self.filename)
        
        # Create new file
        old_filename = self.filename
        self.filename = get_filename()
        self.out = self._make_writer(self.filename, self.fps, self.frame_size)
        print(f"[FILE] Rotated from {old_filename} to {self.filename}")
        self.last_save_time = time.time()
    
    def toggle_pause(self):
        """Toggle recording pause state"""
        self.paused = not self.paused
        print("[PAUSE]" if self.paused else "[RESUME]")
        return self.paused
    
    def save_snapshot(self, frame, folder_path):
        """Save a snapshot image"""
        import datetime
        snapshot_name = os.path.join(
            folder_path,
            datetime.datetime.now().strftime("snapshot_%H%M%S.jpg")
        )
        cv2.imwrite(snapshot_name, frame)
        print(f"[SNAPSHOT] Snapshot saved: {snapshot_name}")
        return snapshot_name
    
    def close(self):
        """Close the video recorder"""
        success = self._close_writer_safely(self.out, self.filename)
        if success:
            print(f"[SUCCESS] Video successfully saved: {self.filename}")
        else:
            print(f"[WARNING] There may have been issues saving: {self.filename}")
        return success
