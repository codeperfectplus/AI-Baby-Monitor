"""
RTSP streaming module for camera connectivity
"""
import cv2
import time
import threading
from config.settings import config


class RTSPReader:
    """Threaded RTSP stream reader with auto-reconnection"""
    
    def __init__(self, url):
        """Initialize RTSP reader"""
        self.url = url
        self.cap = None
        self.connect()
        
        self.lock = threading.Lock()
        self.latest_frame = None
        self.stopped = False
        self.connection_lost = False
        
        # Start reading thread
        t = threading.Thread(target=self.update, daemon=True)
        t.start()
    
    def connect(self):
        """Try to connect to RTSP stream with retries"""
        for attempt in range(config.MAX_RETRIES):
            try:
                print(f"[RTSP] Attempting connection (attempt {attempt + 1}/{config.MAX_RETRIES})...")
                
                # Try different RTSP transport methods
                transports = [
                    f"{self.url}",  # Default
                    f"{self.url.replace('rtsp://', 'rtsp://')}"  # Ensure rtsp prefix
                ]
                
                for transport_url in transports:
                    self.cap = cv2.VideoCapture(transport_url, cv2.CAP_FFMPEG)
                    # Set additional properties for better connection
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_FPS, 25)
                    
                    if self.cap.isOpened():
                        # Test if we can actually read a frame
                        ret, frame = self.cap.read()
                        if ret and frame is not None:
                            print(f"[SUCCESS] RTSP connection successful!")
                            return
                        else:
                            self.cap.release()
                            print(f"[WARNING] Could not read from stream, trying next method...")
                    else:
                        print(f"[WARNING] Could not open stream with {transport_url}")
                
                print(f"[ERROR] Connection attempt {attempt + 1} failed, retrying in {config.RETRY_DELAY} seconds...")
                time.sleep(config.RETRY_DELAY)
                
            except Exception as e:
                print(f"[ERROR] Connection error on attempt {attempt + 1}: {e}")
                time.sleep(config.RETRY_DELAY)
        
        raise RuntimeError(self._get_connection_error_message())
    
    def _get_connection_error_message(self):
        """Generate detailed error message for connection failure"""
        camera_ip = self.url.split('@')[1].split('/')[0] if '@' in self.url else 'unknown'
        return (f"[ERROR] Cannot open RTSP stream after {config.MAX_RETRIES} attempts. Please check:\n"
                f"1. Camera IP address: {camera_ip}\n"
                f"2. Username/password credentials\n"
                f"3. Network connectivity\n"
                f"4. Camera is powered on and accessible")
    
    def update(self):
        """Background thread for reading frames"""
        consecutive_failures = 0
        
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.1)
                continue
                
            grabbed = self.cap.grab()
            if not grabbed:
                consecutive_failures += 1
                if consecutive_failures >= config.MAX_FAILURES:
                    print("[WARNING] Too many consecutive failures, attempting to reconnect...")
                    try:
                        self.cap.release()
                        self.connect()
                        consecutive_failures = 0
                        self.connection_lost = False
                    except Exception as e:
                        print(f"[ERROR] Reconnection failed: {e}")
                        self.connection_lost = True
                        time.sleep(5)  # Wait longer before next attempt
                else:
                    time.sleep(0.01)
                continue
            
            ret, frame = self.cap.read()
            if not ret or frame is None:
                consecutive_failures += 1
                time.sleep(0.01)
                continue
            
            # Reset failure counter on successful read
            consecutive_failures = 0
            self.connection_lost = False
            
            with self.lock:
                self.latest_frame = frame

    def read(self):
        """Get the latest frame"""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        """Stop the reader and release resources"""
        self.stopped = True
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
