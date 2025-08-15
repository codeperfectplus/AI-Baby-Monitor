"""
DeepSORT tracking module for object tracking
"""
from deep_sort_realtime.deepsort_tracker import DeepSort
from config.settings import config
from utils.helpers import calculate_iou, log_line

from services.notification.notification_service import get_notification_service

notification_service = get_notification_service()



class DeepSortTracker:
    """DeepSORT tracking wrapper with child selection logic"""
    
    def __init__(self):
        """Initialize DeepSORT tracker"""
        self.tracker = DeepSort(
            max_age=config.MAX_AGE,
            n_init=config.N_INIT,
            max_cosine_distance=config.MAX_COSINE_DISTANCE,
            nn_budget=config.NN_BUDGET
        )
        print(f"[INFO] DeepSORT tracker initialized for CPU processing")
        
        # Tracking state
        self.child_id = None
        self.track_confidences = {}
        self.track_classes = {}
        self.click_point = None
        
    def update_tracks(self, detections, frame):
        """Update tracks with new detections"""
        return self.tracker.update_tracks(detections, frame=frame)
        
    def map_track_confidences(self, tracks, person_detections):
        """Map confidence scores to tracks"""
        for t in tracks:
            if not t.is_confirmed():
                continue
            l, t_y, r, b = map(int, t.to_ltrb())
            track_rect = (l, t_y, r, b)
            
            # Find the detection with highest IoU overlap
            best_conf = 0.0
            best_iou = 0.0
            best_class = "unknown"
            
            for (dx, dy, dw, dh), conf, class_name in person_detections:
                det_rect = (dx, dy, dx + dw, dy + dh)
                iou = calculate_iou(track_rect, det_rect)
                
                if iou > best_iou:
                    best_iou = iou
                    best_conf = conf
                    best_class = class_name
            
            # Update confidence and class if we found a good match
            if best_iou > 0.3:  # minimum IoU threshold for matching
                self.track_confidences[t.track_id] = best_conf
                self.track_classes[t.track_id] = best_class
        
        # Clean up confidence scores for tracks that no longer exist
        current_track_ids = {t.track_id for t in tracks if t.is_confirmed()}
        self.track_confidences = {tid: conf for tid, conf in self.track_confidences.items() 
                                if tid in current_track_ids}
        self.track_classes = {tid: cls for tid, cls in self.track_classes.items() 
                            if tid in current_track_ids}
    
    def handle_manual_selection(self, tracks):
        """Handle manual child selection via mouse click"""
        if config.MANUAL_CHILD_SELECT and self.child_id is None and self.click_point is not None:
            cx, cy = self.click_point
            for t in tracks:
                if not t.is_confirmed():
                    continue
                l, t_y, r, b = map(int, t.to_ltrb())
                if l <= cx <= r and t_y <= cy <= b:
                    self.child_id = t.track_id
                    log_line(f"Child manually selected: track_id={self.child_id}")
                    notification_service.dispatch_notification("Child Selected", f"Locked to track ID {self.child_id}")
                    break
            self.click_point = None  # consume click
    
    def handle_auto_selection(self, tracks, smallest_det_tlwh):
        """Handle automatic child selection based on smallest person"""
        if self.child_id is None and config.AUTO_SELECT_SMALLEST and smallest_det_tlwh is not None:
            sx, sy, sw, sh = smallest_det_tlwh
            s_rect = (sx, sy, sx + sw, sy + sh)
            best_iou = 0.0
            best_id = None
            
            for t in tracks:
                if not t.is_confirmed():
                    continue
                l, t_y, r, b = map(int, t.to_ltrb())
                track_rect = (l, t_y, r, b)
                iou = calculate_iou(s_rect, track_rect)
                
                if iou > best_iou:
                    best_iou = iou
                    best_id = t.track_id
                    
            if best_id is not None:
                self.child_id = best_id
                log_line(f"Child auto-selected (smallest person): track_id={self.child_id}")
                notification_service.dispatch_notification("Child Selected", f"Auto-selected track ID {self.child_id}")
    
    def get_child_center(self, tracks):
        """Get center coordinates of the selected child"""
        if self.child_id is None:
            return None
            
        for t in tracks:
            if not t.is_confirmed() or t.track_id != self.child_id:
                continue
            l, t_y, r, b = map(int, t.to_ltrb())
            cx = (l + r) // 2
            cy = (t_y + b) // 2
            return (cx, cy)
        
        return None
    
    def set_click_point(self, point):
        """Set mouse click point for manual selection"""
        self.click_point = point
    
    def clear_child_selection(self):
        """Clear child selection and reset state"""
        self.child_id = None
        self.click_point = None
        log_line("Child selection cleared.")
        notification_service.dispatch_notification("Child Selection", "Child selection cleared")
