"""
Visualization and UI rendering module
"""
import cv2
import time
import numpy as np
from config.settings import config


class Visualizer:
    """Handle all visualization and UI rendering"""
    
    def __init__(self, frame_width, frame_height):
        """Initialize visualizer"""
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        if config.SHOW_PREVIEW:
            cv2.namedWindow("Baby Monitor By CodePerfectPlus", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Baby Monitor By CodePerfectPlus", 1280, 720)
    
    def draw_detections(self, frame, all_detections):
        """Draw all non-person detections"""
        annotated = frame.copy()
        
        for det in all_detections:
            if det['class'] != 'person':  # Skip person, they'll be handled by tracker
                x1, y1, x2, y2 = det['bbox']
                class_name = det['class']
                confidence = det['confidence']
                
                # Use different colors for different object types
                if class_name == 'bed':
                    color = (0, 255, 255)  # Yellow for bed
                else:
                    color = (128, 128, 128)  # Gray for other objects
                
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name} ({confidence:.2f})"
                cv2.putText(annotated, label, (x1, y1 - 6),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return annotated
    
    def draw_safe_zone(self, frame, bed_box, safe_zone):
        """Draw bed and safe zone"""
        if not config.USE_BED_SAFE_ZONE or bed_box is None:
            return frame
            
        # Draw bed
        bx1, by1, bx2, by2 = bed_box
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
        
        # Draw expanded detection area (bed + margin for child detection)
        margin = 50
        expanded_x1 = max(0, bx1 - margin)
        expanded_y1 = max(0, by1 - margin)
        expanded_x2 = min(frame.shape[1], bx2 + margin)
        expanded_y2 = min(frame.shape[0], by2 + margin)
        
        # Draw detection area with dashed line effect
        cv2.rectangle(frame, (expanded_x1, expanded_y1), (expanded_x2, expanded_y2), (255, 255, 0), 1)
        cv2.putText(frame, "Child Detection Area", (expanded_x1, expanded_y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Draw safe zone
        if safe_zone is not None:
            sx1, sy1, sx2, sy2 = safe_zone
            cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), (0, 255, 0), 2)
            cv2.putText(frame, "Safe zone", (sx1, sy1-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame
    
    def draw_tracks(self, frame, tracks, child_id, track_confidences, track_classes):
        """Draw tracking information"""
        child_center = None
        
        for t in tracks:
            if not t.is_confirmed():
                continue
            l, t_y, r, b = map(int, t.to_ltrb())
            tid = t.track_id

            color = (0, 255, 0) if tid == child_id else (255, 0, 0)
            cv2.rectangle(frame, (l, t_y), (r, b), color, 2)
            
            # Show ID, class name, and confidence on the track box
            label = f"ID {tid}"
            if tid in track_classes:
                class_name = track_classes[tid]
                label = f"{class_name} ID {tid}"
            if tid in track_confidences:
                conf = track_confidences[tid]
                label += f" ({conf:.2f})"
            cv2.putText(frame, label, (l, t_y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if tid == child_id:
                cx = (l + r) // 2
                cy = (t_y + b) // 2
                child_center = (cx, cy)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)
        
        return frame, child_center
    
    def draw_sleep_indicators(self, frame, child_center, sleep_monitor):
        """Draw sleep/wake indicators"""
        if child_center is None or not sleep_monitor.enabled:
            return frame
            
        # Visual sleep indicator
        if sleep_monitor.child_is_sleeping:
            cv2.putText(frame, "SLEEPING [ZZZ]", (child_center[0] - 50, child_center[1] + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        return frame
    
    def draw_fall_risk_warning(self, frame, safe_zone, is_at_risk):
        """Draw fall risk warning"""
        if safe_zone is None or not is_at_risk:
            return frame
            
        sx1, sy1, sx2, sy2 = safe_zone
        cv2.putText(frame, "RISK: Near edge!", (sx1, sy1 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        
        return frame
    
    def draw_wake_alert(self, frame, sleep_monitor):
        """Draw wake up alert"""
        if sleep_monitor.wake_alert_display_time == 0:
            return frame
            
        if (time.time() - sleep_monitor.wake_alert_display_time) < 5.0:
            alert_text = "[WAKE] CHILD WOKE UP! [WAKE]"
            # Calculate center position for alert
            (alert_w, alert_h), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 3)
            alert_x = (self.frame_width - alert_w) // 2
            alert_y = (self.frame_height - alert_h) // 2
            
            # Draw alert background
            cv2.rectangle(frame, (alert_x - 20, alert_y - alert_h - 20), 
                         (alert_x + alert_w + 20, alert_y + 20), (0, 0, 0), -1)  # Black background
            cv2.rectangle(frame, (alert_x - 20, alert_y - alert_h - 20), 
                         (alert_x + alert_w + 20, alert_y + 20), (0, 255, 255), 4)  # Yellow border
            cv2.putText(frame, alert_text, (alert_x, alert_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
        
        return frame
    
    def show_connection_status(self, connection_lost):
        """Show connection status when no frame is available"""
        if not config.SHOW_PREVIEW:
            return
            
        # Create a black frame to show status
        status_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        if connection_lost:
            cv2.putText(status_frame, "CONNECTION LOST - RECONNECTING...", 
                       (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            cv2.putText(status_frame, "WAITING FOR CAMERA STREAM...", 
                       (80, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow("Baby Monitor By CodePerfectPlus", status_frame)
        cv2.waitKey(1)
    
    def show_frame(self, frame):
        """Display frame in preview window"""
        if config.SHOW_PREVIEW:
            cv2.imshow("Baby Monitor By CodePerfectPlus", frame)
            return cv2.waitKey(1) & 0xFF
        else:
            return cv2.waitKey(1) & 0xFF
    
    def set_mouse_callback(self, callback):
        """Set mouse callback for manual selection"""
        if config.SHOW_PREVIEW:
            cv2.setMouseCallback("Baby Monitor By CodePerfectPlus", callback)
    
    def cleanup(self):
        """Cleanup visualization resources"""
        cv2.destroyAllWindows()
