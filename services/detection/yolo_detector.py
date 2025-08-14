"""
YOLO detection module for object detection
"""
import torch
from ultralytics import YOLO

from config.settings import config
from services.detection.base_detector import BaseDetector

class YOLODetector(BaseDetector):
    """YOLO object detection wrapper"""
    
    def __init__(self):
        """Initialize YOLO model"""
        # Force CPU-only processing
        torch.cuda.is_available = lambda: False
        print("[INFO] Forced PyTorch to use CPU only")
        
        # Load YOLO model
        self.model = YOLO(config.MODEL_PATH)
        self.model.to('cpu')
        print(f"[INFO] YOLOv8 model loaded on CPU device")
        print(f"[INFO] Using YOLO model: {config.MODEL_PATH} (CPU-only mode)")
        
        # Bed detection caching
        self.cached_bed_box = None
        self.bed_detection_frames = 0
        self.bed_confirmed_threshold = 1  # Confirm bed after 1 consistent detections
        self.bed_redetect_interval = 7200  # Re-detect bed every 7200 frames (~4 minutes at 30fps)
        self.frames_since_bed_detection = 0
    
    def detect(self, frame):
        """
        Perform object detection on frame
        
        Args:
            frame: Input frame for detection
            
        Returns:
            tuple: (detections_for_tracker, bed_box, all_detections)
                - detections_for_tracker: List of (tlwh, confidence, class) for persons
                - bed_box: Bed bounding box if detected, else None
                - all_detections: List of all detections with bbox, class, confidence
        """
        # Check if we should use cached bed or re-detect
        should_detect_bed = (
            self.cached_bed_box is None or  # No cached bed yet
            self.frames_since_bed_detection >= self.bed_redetect_interval  # Time to re-validate
        )
        
        # Increment frame counter
        self.frames_since_bed_detection += 1
        
        results = self.model.predict(
            frame, 
            conf=config.CONFIDENCE_THRESHOLD, 
            verbose=False, 
            device='cpu'
        )
        res = results[0]
        
        # Prepare detection data
        dets = []
        smallest_area = None
        smallest_det_tlwh = None
        person_detections = []
        all_detections = []
        detected_bed_box = None
        
        names = res.names
        
        if res.boxes is not None and len(res.boxes) > 0:
            # Note: Type checking may show errors but this works at runtime with YOLO tensors
            xyxy = res.boxes.xyxy.cpu().numpy()  # type: ignore
            clss = res.boxes.cls.cpu().numpy().astype(int)  # type: ignore
            confs = res.boxes.conf.cpu().numpy()  # type: ignore
            
            # First pass: Find bed bounding box (only if we should detect it)
            if should_detect_bed:
                for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
                    label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
                    
                    if label == "bed":
                        detected_bed_box = (int(x1), int(y1), int(x2), int(y2))
                        break  # Use first bed detection
                
                # Update cached bed if detected
                if detected_bed_box is not None:
                    if self.cached_bed_box is None:
                        # First time detecting bed
                        self.bed_detection_frames = 1
                        print(f"[BED] First bed detection: {detected_bed_box}")
                    else:
                        # Check if new detection is similar to cached one
                        cached_x1, cached_y1, cached_x2, cached_y2 = self.cached_bed_box
                        new_x1, new_y1, new_x2, new_y2 = detected_bed_box
                        
                        # Calculate difference threshold (10% of frame size)
                        diff_threshold = min(frame.shape[0], frame.shape[1]) * 0.1
                        
                        if (abs(cached_x1 - new_x1) < diff_threshold and
                            abs(cached_y1 - new_y1) < diff_threshold and
                            abs(cached_x2 - new_x2) < diff_threshold and
                            abs(cached_y2 - new_y2) < diff_threshold):
                            self.bed_detection_frames += 1
                        else:
                            # Significant change, reset counter
                            self.bed_detection_frames = 1
                            print(f"[BED] Bed position changed, resetting cache")
                    
                    # Confirm bed if we've seen it consistently
                    if self.bed_detection_frames >= self.bed_confirmed_threshold:
                        self.cached_bed_box = detected_bed_box
                        self.frames_since_bed_detection = 0  # Reset counter
                        print(f"[BED] Bed confirmed and cached: {detected_bed_box}")
                else:
                    # No bed detected, keep using cached if available
                    if self.cached_bed_box is not None:
                        print(f"[BED] No bed detected, using cached: {self.cached_bed_box}")
            
            # Use cached bed box for person filtering
            bed_box = self.cached_bed_box
            
            # Store all detections for display (excluding bed to avoid redundant display)
            for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
                label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
                
                bbox_info = {
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'class': label,
                    'confidence': float(conf)
                }
                all_detections.append(bbox_info)
            
            # Second pass: Filter person detections based on bed area
            for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
                label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
                    
                if label == "person":
                    # Check if person is within bed area (if bed detected)
                    person_in_bed_area = True  # Default: accept all persons if no bed
                    
                    if bed_box is not None:
                        # Calculate overlap between person and bed
                        bed_x1, bed_y1, bed_x2, bed_y2 = bed_box
                        person_center_x = (x1 + x2) / 2
                        person_center_y = (y1 + y2) / 2
                        
                        # Check if person center is within expanded bed area
                        # Add some margin to bed area to catch children near bed edges
                        margin = 50  # pixels
                        expanded_bed_x1 = max(0, bed_x1 - margin)
                        expanded_bed_y1 = max(0, bed_y1 - margin)
                        expanded_bed_x2 = min(frame.shape[1], bed_x2 + margin)
                        expanded_bed_y2 = min(frame.shape[0], bed_y2 + margin)
                        
                        person_in_bed_area = (
                            expanded_bed_x1 <= person_center_x <= expanded_bed_x2 and
                            expanded_bed_y1 <= person_center_y <= expanded_bed_y2
                        )
                    
                    # Only include person if they are in bed area (or no bed detected)
                    if person_in_bed_area:
                        w = max(1, int(x2 - x1))
                        h = max(1, int(y2 - y1))
                        tlwh = [int(x1), int(y1), w, h]
                        dets.append((tlwh, float(conf), "person"))
                        person_detections.append((tlwh, float(conf), label))
                        
                        area = w * h
                        if config.AUTO_SELECT_SMALLEST and (smallest_area is None or area < smallest_area):
                            smallest_area = area
                            smallest_det_tlwh = tlwh
        
        # Always add cached bed to all_detections if available (for visualization)
        if self.cached_bed_box is not None:
            bed_already_in_detections = any(
                det['class'] == 'bed' for det in all_detections
            )
            if not bed_already_in_detections:
                all_detections.append({
                    'bbox': self.cached_bed_box,
                    'class': 'bed',
                    'confidence': 0.95  # High confidence for cached bed
                })
        
        return dets, self.cached_bed_box, all_detections, person_detections, smallest_det_tlwh
    
    def reset_bed_cache(self):
        """Reset cached bed detection (useful if bed position changes)"""
        self.cached_bed_box = None
        self.bed_detection_frames = 0
        self.frames_since_bed_detection = 0
        print("[BED] Bed cache reset - will re-detect bed location")
    
    def get_bed_status(self):
        """Get current bed detection status"""
        return {
            'cached': self.cached_bed_box is not None,
            'bed_box': self.cached_bed_box,
            'frames_confirmed': self.bed_detection_frames,
            'frames_since_detection': self.frames_since_bed_detection
        }
