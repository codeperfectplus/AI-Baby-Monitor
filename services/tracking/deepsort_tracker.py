"""
DeepSORT tracking module for object tracking with enhanced child (baby) selection.

Enhancement:
- Multi-frame average height based selection instead of a single-frame smallest bbox.
- Stability requirement to avoid flickering selection.
"""

from collections import deque
from statistics import mean, median

from deep_sort_realtime.deepsort_tracker import DeepSort
from config.settings import config
from utils.helpers import calculate_iou, log_line
from services.notification.notification_service import get_notification_service

notification_service = get_notification_service()


class DeepSortTracker:
    """DeepSORT tracking wrapper with child selection logic (manual + improved automatic)."""
    
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

        # Height statistics for multi-frame averaging
        # track_height_history: track_id -> deque of recent heights
        self.track_height_history = {}
        # track_avg_height: track_id -> rolling average height
        self.track_avg_height = {}
        # candidate_stability: track_id -> consecutive frames that track meets "child" criteria
        self.candidate_stability = {}

        # Config-driven parameters with graceful fallbacks
        self.history_size = getattr(config, "CHILD_HISTORY_SIZE", 30)
        self.min_history = getattr(config, "CHILD_MIN_HISTORY", 5)
        self.height_ratio_threshold = getattr(config, "CHILD_HEIGHT_RATIO_THRESHOLD", 0.75)
        self.stability_frames = getattr(config, "CHILD_STABILITY_FRAMES", 3)
    
    def update_tracks(self, detections, frame):
        """Update tracks with new detections"""
        tracks = self.tracker.update_tracks(detections, frame=frame)
        # Update height stats every frame for confirmed tracks
        self._update_height_statistics(tracks)
        return tracks

    def _update_height_statistics(self, tracks):
        """Maintain rolling height statistics for each confirmed track."""
        current_ids = set()
        for t in tracks:
            if not t.is_confirmed():
                continue
            l, top, r, b = map(int, t.to_ltrb())
            h = max(1, b - top)
            tid = t.track_id
            current_ids.add(tid)
            dq = self.track_height_history.get(tid)
            if dq is None:
                dq = deque(maxlen=self.history_size)
                self.track_height_history[tid] = dq
            dq.append(h)
            self.track_avg_height[tid] = sum(dq) / len(dq)

        # Cleanup histories for tracks that vanished
        removed = set(self.track_height_history.keys()) - current_ids
        for tid in removed:
            self.track_height_history.pop(tid, None)
            self.track_avg_height.pop(tid, None)
            self.candidate_stability.pop(tid, None)

    def map_track_confidences(self, tracks, person_detections):
        """Map confidence scores to tracks using IoU with current detections."""
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
        self.track_confidences = {
            tid: conf for tid, conf in self.track_confidences.items()
            if tid in current_track_ids
        }
        self.track_classes = {
            tid: cls for tid, cls in self.track_classes.items()
            if tid in current_track_ids
        }
    
    def handle_manual_selection(self, tracks):
        """Handle manual child selection via mouse click."""
        if getattr(config, "MANUAL_CHILD_SELECT", False) and self.child_id is None and self.click_point is not None:
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
    
    def handle_auto_selection(self, tracks, smallest_det_tlwh=None):
        """
        Enhanced automatic child selection:
        - Use multi-frame height averages to identify the smallest (baby) among people.
        - A track is a candidate if:
            * It has at least min_history frames of height data.
            * Its average height ratio vs global avg (or median) is below height_ratio_threshold.
        - Track must satisfy the candidate condition for stability_frames consecutive frames before locking.
        - Fallback: if no candidate, optionally revert to original smallest bbox (current-frame) logic.
        """
        if self.child_id is not None:
            return  # Already selected

        if not getattr(config, "AUTO_SELECT_SMALLEST", True):
            return

        # Gather usable tracks (confirmed & with history)
        usable_tracks = []
        for t in tracks:
            if not t.is_confirmed():
                continue
            tid = t.track_id
            if tid not in self.track_height_history:
                continue
            if len(self.track_height_history[tid]) < self.min_history:
                continue
            usable_tracks.append(tid)

        if not usable_tracks:
            # Not enough history yet -> fallback if smallest_det_tlwh provided
            self._fallback_smallest_bbox(tracks, smallest_det_tlwh)
            return

        # Compute robust global height references (average of averages + median)
        avg_heights = [self.track_avg_height[tid] for tid in usable_tracks]
        if not avg_heights:
            self._fallback_smallest_bbox(tracks, smallest_det_tlwh)
            return

        global_avg = mean(avg_heights)
        global_median = median(avg_heights)
        # Use a combined reference (slightly robust); choose the smaller of avg/median to be conservative
        ref_height = min(global_avg, global_median)

        # Build candidate set
        candidates = []
        for tid in usable_tracks:
            track_avg = self.track_avg_height[tid]
            ratio = track_avg / max(ref_height, 1.0)
            if ratio <= self.height_ratio_threshold:
                candidates.append((tid, track_avg, ratio))

        if not candidates:
            # No multi-frame candidate -> fallback to smallest
            self._fallback_smallest_bbox(tracks, smallest_det_tlwh)
            return

        # Choose candidate with smallest average height; if tie, smallest ratio
        candidates.sort(key=lambda x: (x[1], x[2]))
        best_tid, best_avg_height, best_ratio = candidates[0]

        # Update stability counters
        # Reset counters for non-candidates
        candidate_ids = {c[0] for c in candidates}
        for tid in list(self.candidate_stability.keys()):
            if tid not in candidate_ids:
                self.candidate_stability[tid] = 0

        self.candidate_stability[best_tid] = self.candidate_stability.get(best_tid, 0) + 1

        if self.candidate_stability[best_tid] >= self.stability_frames:
            # Lock selection
            self.child_id = best_tid
            log_line(
                f"Child auto-selected (multi-frame avg height). "
                f"track_id={self.child_id} avg_height={best_avg_height:.2f} "
                f"ratio={best_ratio:.3f} ref_height={ref_height:.2f}"
            )
            notification_service.dispatch_notification(
                "Child Selected",
                f"Auto-selected track ID {self.child_id} (avg height ratio {best_ratio:.2f})"
            )

    def _fallback_smallest_bbox(self, tracks, smallest_det_tlwh):
        """
        Original single-frame fallback:
        Use provided smallest detection (if any) and map via IoU to a track.
        """
        if smallest_det_tlwh is None:
            return
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
            log_line(f"Child auto-selected (fallback smallest bbox): track_id={self.child_id}")
            notification_service.dispatch_notification("Child Selected", f"Fallback-selected track ID {self.child_id}")

    def get_child_center(self, tracks):
        """Get center coordinates of the selected child."""
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
        """Set mouse click point for manual selection."""
        self.click_point = point
    
    def clear_child_selection(self):
        """Clear child selection and reset state."""
        self.child_id = None
        self.click_point = None
        self.candidate_stability.clear()
        log_line("Child selection cleared.")
        notification_service.dispatch_notification("Child Selection", "Child selection cleared")