"""
Streaming services for RTSP Baby Monitor
"""
import cv2
import threading
import time
import base64
import gc
import psutil
from collections import deque
from config.settings import config
from services.detection.yolo_detector import YOLODetector
from services.tracking.deepsort_tracker import DeepSortTracker
from services.monitoring.monitors import SleepMonitor, SafetyMonitor
from services.visualization.visualizer import Visualizer
from services.streaming.rtsp_reader import RTSPReader


class FrameMemoryPool:
    """Memory pool for efficient frame management"""
    def __init__(self, pool_size=10):
        self.pool = deque(maxlen=pool_size)
        self.lock = threading.Lock()
    
    def get_frame_buffer(self, shape):
        with self.lock:
            if self.pool:
                buffer = self.pool.popleft()
                if buffer.shape == shape:
                    return buffer
            return None
    
    def return_frame_buffer(self, buffer):
        with self.lock:
            self.pool.append(buffer)


class WebStreamManager(threading.Thread):
    """Dedicated thread for managing web streaming with load balancing"""
    
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio
        self.running = True
        self.frame_queue = deque(maxlen=3)  # Small buffer for latest frames
        self.queue_lock = threading.Lock()
        self.client_connections = 0
        self.last_frame_time = 0
        self.adaptive_quality = 80
        self.adaptive_fps = 25
        self.daemon = True
        
    def add_frame(self, frame):
        """Add frame to streaming queue (called by AI thread)"""
        current_time = time.time()
        # Adaptive frame rate based on client load
        min_interval = 1.0 / self.adaptive_fps
        
        if current_time - self.last_frame_time >= min_interval:
            with self.queue_lock:
                # Create web-optimized frame
                web_frame = self._optimize_frame_for_web(frame)
                self.frame_queue.append(web_frame)
                self.last_frame_time = current_time
    
    def _optimize_frame_for_web(self, frame):
        """Optimize frame for web streaming based on client load"""
        # Dynamic quality adjustment based on number of clients
        if self.client_connections > 3:
            quality = max(50, self.adaptive_quality - 20)
            scale = 0.7
        elif self.client_connections > 1:
            quality = max(60, self.adaptive_quality - 10)
            scale = 0.8
        else:
            quality = self.adaptive_quality
            scale = 1.0
        
        # Resize frame if needed
        if scale < 1.0:
            height, width = frame.shape[:2]
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        return frame, quality
    
    def get_latest_frame(self):
        """Get latest frame for streaming"""
        with self.queue_lock:
            if self.frame_queue:
                return self.frame_queue[-1]  # Get most recent frame
        return None, None
    
    def update_client_count(self, count):
        """Update active client count for load balancing"""
        self.client_connections = count
        # Adjust streaming parameters based on load
        if count > 5:
            self.adaptive_fps = 15
            self.adaptive_quality = 60
        elif count > 2:
            self.adaptive_fps = 20
            self.adaptive_quality = 70
        else:
            self.adaptive_fps = 25
            self.adaptive_quality = 80
    
    def run(self):
        """WebSocket streaming loop"""
        while self.running:
            frame_data, quality = self.get_latest_frame()
            if frame_data is not None:
                try:
                    # Encode frame with adaptive quality
                    quality_val = int(quality) if quality is not None else 80
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality_val]
                    ret, buffer = cv2.imencode('.jpg', frame_data, encode_params)
                    
                    if ret:
                        # Convert to base64 for WebSocket transmission
                        frame_b64 = base64.b64encode(buffer).decode('utf-8')
                        
                        # Send to all connected clients via WebSocket
                        self.socketio.emit('video_frame', {'frame': frame_b64})
                        
                        # Memory cleanup
                        del buffer, frame_b64
                        
                except Exception as e:
                    print(f"WebSocket streaming error: {e}")
            
            # Adaptive sleep based on client load
            sleep_time = 1.0 / self.adaptive_fps
            time.sleep(sleep_time)
    
    def stop(self):
        self.running = False


class AIBabyMonitorStreamer(threading.Thread):
    """Main AI processing and streaming service"""
    
    def __init__(self, web_stream_manager):
        super().__init__()
        self.web_stream_manager = web_stream_manager
        self.detector = YOLODetector()
        self.tracker = DeepSortTracker()
        self.sleep_monitor = SleepMonitor()
        self.safety_monitor = SafetyMonitor()
        self.reader = RTSPReader(config.rtsp_url)
        
        # Initialize frame dimensions
        frame = None
        while frame is None:
            frame = self.reader.read()
            time.sleep(0.05)
        self.frame_height, self.frame_width = frame.shape[:2]
        self.frame_shape = frame.shape
        
        # Initialize components
        self.visualizer = Visualizer(self.frame_width, self.frame_height)
        from services.recording.video_recorder import VideoRecorder
        self.recorder = VideoRecorder(config.TARGET_FPS, (self.frame_width, self.frame_height))
        self.save_annotated = config.SAVE_ANNOTATED
        self.running = True
        
        # Memory management
        self.frame_count = 0
        self.gc_interval = 100  # Run garbage collection every 100 frames
        
        # Pre-allocate buffers
        self.working_frame = None
        self.annotated_frame = None
        
        # Shared frame access
        self.latest_frame = None
        self.lock = threading.Lock()

    def run(self):
        """Main AI processing loop"""
        while self.running:
            # Get frame with memory management
            frame = self.reader.read()
            if frame is None:
                continue
            
            # Use memory pool for working frames
            if self.working_frame is None:
                self.working_frame = frame.copy()
            else:
                # Reuse existing buffer
                self.working_frame[:] = frame
            
            try:
                # AI pipeline (reusing memory where possible)
                dets, bed_box, all_detections, person_detections, smallest_det_tlwh = \
                    self.detector.detect(self.working_frame)
                
                tracks = self.tracker.update_tracks(dets, self.working_frame)
                self.tracker.map_track_confidences(tracks, person_detections)
                self.tracker.handle_manual_selection(tracks)
                self.tracker.handle_auto_selection(tracks, smallest_det_tlwh)
                
                child_center = self.tracker.get_child_center(tracks)
                self.sleep_monitor.update(child_center)
                
                # Reuse annotated frame buffer
                if self.annotated_frame is None:
                    annotated = self.visualizer.draw_detections(self.working_frame, all_detections)
                    self.annotated_frame = annotated.copy()
                else:
                    self.annotated_frame[:] = self.working_frame
                    annotated = self.visualizer.draw_detections(self.annotated_frame, all_detections)
                
                safe_zone = self.safety_monitor.get_safe_zone(bed_box)
                annotated = self.visualizer.draw_safe_zone(annotated, bed_box, safe_zone)
                annotated, _ = self.visualizer.draw_tracks(
                    annotated, tracks, self.tracker.child_id,
                    self.tracker.track_confidences, self.tracker.track_classes
                )
                
                is_at_risk = self.safety_monitor.check_fall_risk(child_center, safe_zone)
                annotated = self.visualizer.draw_fall_risk_warning(annotated, safe_zone, is_at_risk)
                annotated = self.visualizer.draw_sleep_indicators(annotated, child_center, self.sleep_monitor)
                annotated = self.visualizer.draw_wake_alert(annotated, self.sleep_monitor)
                
                # Record video
                frame_to_save = annotated if self.save_annotated else self.working_frame
                self.recorder.write_frame(frame_to_save)
                self.recorder.check_rotation()
                
                # Update shared frames with memory management
                with self.lock:
                    if self.latest_frame is None:
                        self.latest_frame = annotated.copy()
                    else:
                        self.latest_frame[:] = annotated
                
                # Send to web streaming thread
                self.web_stream_manager.add_frame(annotated)
                
                # Periodic garbage collection
                self.frame_count += 1
                if self.frame_count % self.gc_interval == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"AI Pipeline error: {e}")
                continue
            
            time.sleep(1.0 / config.TARGET_FPS)

    def stop(self):
        self.running = False
        self.reader.stop()
        self.recorder.close()
        self.web_stream_manager.stop()

    def get_sleep_metrics(self):
        """Returns the current sleep state and sleep time from the sleep monitor."""
        sleep_state = self.sleep_monitor.get_state() if hasattr(self.sleep_monitor, 'get_state') else 'Unknown'
        sleep_time = self.sleep_monitor.get_sleep_time() if hasattr(self.sleep_monitor, 'get_sleep_time') else '1m'
        return sleep_state, sleep_time
    
    def get_latest_frame(self):
        """Get the latest processed frame"""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None


class StreamingService:
    """Main streaming service orchestrator"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.web_stream_manager = None
        self.ai_streamer = None
        self.active_clients = set()
        self.frame_pool = FrameMemoryPool()
        
    def initialize(self):
        """Initialize streaming components"""
        try:
            # Initialize web stream manager
            self.web_stream_manager = WebStreamManager(self.socketio)
            
            # Initialize AI streamer
            self.ai_streamer = AIBabyMonitorStreamer(self.web_stream_manager)
            
            return True
        except Exception as e:
            print(f"Failed to initialize streaming service: {e}")
            return False
    
    def start(self):
        """Start streaming services"""
        if self.ai_streamer and self.web_stream_manager:
            self.ai_streamer.daemon = True
            self.ai_streamer.start()
            self.web_stream_manager.start()
            print("[INFO] All streaming components started successfully")
            return True
        return False
    
    def stop(self):
        """Stop streaming services"""
        if self.ai_streamer:
            self.ai_streamer.stop()
        if self.web_stream_manager:
            self.web_stream_manager.stop()
    
    def get_metrics(self):
        """Get system and streaming metrics"""
        # System metrics
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        net_io = psutil.net_io_counters()
        network = min(100, (net_io.bytes_sent + net_io.bytes_recv) / 1e7)
        
        # Application metrics
        detection_rate = 98  # TODO: get from detector
        room_temp = 24
        
        # Sleep metrics (only if streamer is available)
        if self.ai_streamer is not None:
            sleep_state, sleep_time = self.ai_streamer.get_sleep_metrics()
        else:
            sleep_state, sleep_time = 'Offline', '0m'
        
        # Streaming metrics
        active_client_count = len(self.active_clients)
        streaming_fps = self.web_stream_manager.adaptive_fps if self.web_stream_manager is not None else 0
        streaming_quality = self.web_stream_manager.adaptive_quality if self.web_stream_manager is not None else 0
        
        return {
            'cpu': cpu,
            'memory': memory,
            'network': network,
            'detection_rate': detection_rate,
            'sleep_state': sleep_state,
            'room_temp': room_temp,
            'sleep_time': sleep_time,
            'streaming': {
                'active_clients': active_client_count,
                'adaptive_fps': streaming_fps,
                'adaptive_quality': streaming_quality
            }
        }
    
    def add_client(self):
        """Add a client and return client ID"""
        import uuid
        client_id = str(uuid.uuid4())
        self.active_clients.add(client_id)
        
        if self.web_stream_manager:
            self.web_stream_manager.update_client_count(len(self.active_clients))
        
        return client_id, len(self.active_clients)
    
    def remove_client(self):
        """Remove a client"""
        if self.active_clients:
            self.active_clients.pop()
        
        if self.web_stream_manager:
            self.web_stream_manager.update_client_count(len(self.active_clients))
        
        return len(self.active_clients)
    
    def update_quality(self, quality):
        """Update streaming quality"""
        if self.web_stream_manager:
            self.web_stream_manager.adaptive_quality = max(30, min(100, quality))
            return self.web_stream_manager.adaptive_quality
        return 80


# Global streaming service instance
streaming_service = None

def get_streaming_service():
    """Get the global streaming service instance"""
    global streaming_service
    return streaming_service

def initialize_streaming_service(socketio):
    """Initialize the global streaming service"""
    global streaming_service
    streaming_service = StreamingService(socketio)
    return streaming_service
