"""
YOLO detection module for object detection
"""
import os
import time
import torch
from ultralytics import YOLO

from config.settings import config
from services.detection.base_detector import BaseDetector

class YOLODetector(BaseDetector):
    """YOLO object detection wrapper with bed/person filtering and caching"""
    
    def __init__(self, classes=('person', 'bed')):
        """Initialize YOLO model
        Args:
            classes: Iterable of class names to request from YOLO for efficiency
        """
        # --- Reverted: force CPU exactly like initial script ---
        torch.cuda.is_available = lambda: False  # type: ignore
        self.device = 'cpu'
        print("[INFO] Forced PyTorch to use CPU only")

        # Load YOLO model (robust fallback if path missing)
        model_path = config.YOLO_MODEL_PATH
        if not os.path.exists(model_path):
            print(f"[WARN] Model path not found: {model_path}. Falling back to model name {config.YOLO_MODEL_NAME}")
            model_path = config.YOLO_MODEL_NAME
        try:
            t0 = time.perf_counter()
            self.model = YOLO(model_path)
            load_ms = (time.perf_counter() - t0) * 1000
            print(f"[INFO] YOLO model loaded from '{model_path}' in {load_ms:.1f} ms")
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Failed to load YOLO model: {e}")
        self.model.to('cpu')
        print(f"[INFO] YOLOv8 model loaded on CPU device")
        print(f"[INFO] Using YOLO model: {model_path} (CPU-only mode)")

        # Class filtering setup
        # Ultralytics stores names in model.model.names (dict[int,str])
        raw_names = getattr(self.model.model, 'names', {})  # type: ignore[attr-defined]
        if isinstance(raw_names, dict):
            self.class_name_map = raw_names
        else:
            # Fallback if list-like
            self.class_name_map = {i: n for i, n in enumerate(list(raw_names))}
        self.inv_name_map = {v: k for k, v in self.class_name_map.items()}

        self.target_class_ids = []
        for cname in classes:
            cid = self.inv_name_map.get(cname)
            if cid is not None:
                self.target_class_ids.append(cid)
        if not self.target_class_ids:
            # If requested classes not available, disable filtering
            self.target_class_ids = None  # type: ignore
            print("[WARN] Requested classes not found in model; disabling class filter")
        else:
            print(f"[INFO] Filtering classes: {[self.class_name_map[c] for c in self.target_class_ids]}")

        # Bed class id (may be None if model lacks 'bed')
        self.bed_class_id = self.inv_name_map.get('bed')

        # Bed detection caching
        self.cached_bed_box = None
        self.bed_detection_frames = 0
        self.bed_confirmed_threshold = 1  # configurable if needed
        self.bed_redetect_interval = 7200  # frames
        self.frames_since_bed_detection = 0

        # Performance metrics
        self.last_inference_ms = 0.0

    def update_confidence(self, conf: float):
        """Update runtime confidence threshold"""
        conf = max(0.01, min(conf, 0.99))
        config.CONFIDENCE_THRESHOLD = conf  # type: ignore[attr-defined]
        print(f"[INFO] Updated detection confidence to {conf}")

    def detect(self, frame):
        """
        Perform object detection on frame
        Returns tuple: (detections_for_tracker, bed_box, all_detections, person_detections, smallest_det_tlwh)
        """
        if frame is None:
            return [], self.cached_bed_box, [], [], None

        should_detect_bed = (
            self.cached_bed_box is None or
            self.frames_since_bed_detection >= self.bed_redetect_interval
        )
        self.frames_since_bed_detection += 1

        # Inference
        t0 = time.perf_counter()
        with torch.no_grad():
            results = self.model.predict(
                frame,
                conf=config.CONFIDENCE_THRESHOLD,
                verbose=False,
                device='cpu',
                classes=self.target_class_ids
            )
        self.last_inference_ms = (time.perf_counter() - t0) * 1000

        if not results:
            return [], self.cached_bed_box, [], [], None
        res = results[0]

        dets = []
        smallest_area = None
        smallest_det_tlwh = None
        person_detections = []
        all_detections = []
        detected_bed_box = None

        names = getattr(res, 'names', self.class_name_map)

        if res.boxes is None or len(res.boxes) == 0:
            # Re-add cached bed if present for visualization
            if self.cached_bed_box is not None:
                all_detections.append({
                    'bbox': self.cached_bed_box,
                    'class': 'bed',
                    'confidence': 0.95
                })
            return dets, self.cached_bed_box, all_detections, person_detections, smallest_det_tlwh

        # Tensors -> numpy
        xyxy = res.boxes.xyxy.cpu().numpy()  # type: ignore
        clss = res.boxes.cls.cpu().numpy().astype(int)  # type: ignore
        confs = res.boxes.conf.cpu().numpy()  # type: ignore

        # --- Pass 1: Optional bed detection ---
        if should_detect_bed and config.USE_BED_SAFE_ZONE and self.bed_class_id is not None:
            for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
                label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
                if label == 'bed':
                    detected_bed_box = (int(x1), int(y1), int(x2), int(y2))
                    break
            if detected_bed_box is not None:
                if self.cached_bed_box is None:
                    self.bed_detection_frames = 1
                else:
                    cx1, cy1, cx2, cy2 = self.cached_bed_box
                    nx1, ny1, nx2, ny2 = detected_bed_box
                    diff_threshold = min(frame.shape[0], frame.shape[1]) * 0.1
                    if (abs(cx1 - nx1) < diff_threshold and
                        abs(cy1 - ny1) < diff_threshold and
                        abs(cx2 - nx2) < diff_threshold and
                        abs(cy2 - ny2) < diff_threshold):
                        self.bed_detection_frames += 1
                    else:
                        self.bed_detection_frames = 1
                        print("[BED] Position shift detected; resetting validation")
                if self.bed_detection_frames >= self.bed_confirmed_threshold:
                    self.cached_bed_box = detected_bed_box
                    self.frames_since_bed_detection = 0
            else:
                if self.cached_bed_box is not None:
                    print("[BED] No bed this frame; using cached")

        bed_box = self.cached_bed_box

        # --- Pass 2: Collect all detections ---
        for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
            label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
            all_detections.append({
                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                'class': label,
                'confidence': float(conf)
            })

        # --- Pass 3: Person filtering (inside bed if available) ---
        for (x1, y1, x2, y2), cls_id, conf in zip(xyxy, clss, confs):
            label = names.get(int(cls_id), str(cls_id)) if isinstance(names, dict) else names[int(cls_id)]  # type: ignore
            if label != 'person':
                continue
            person_in_bed_area = True
            if bed_box is not None and config.USE_BED_SAFE_ZONE:
                bed_x1, bed_y1, bed_x2, bed_y2 = bed_box
                person_center_x = (x1 + x2) / 2
                person_center_y = (y1 + y2) / 2
                # Margin relative to bed size (fallback to 50px)
                margin = max(50, int((bed_x2 - bed_x1) * 0.08))
                expanded_x1 = max(0, bed_x1 - margin)
                expanded_y1 = max(0, bed_y1 - margin)
                expanded_x2 = min(frame.shape[1], bed_x2 + margin)
                expanded_y2 = min(frame.shape[0], bed_y2 + margin)
                person_in_bed_area = (
                    expanded_x1 <= person_center_x <= expanded_x2 and
                    expanded_y1 <= person_center_y <= expanded_y2
                )
            if person_in_bed_area:
                w = max(1, int(x2 - x1))
                h = max(1, int(y2 - y1))
                tlwh = [int(x1), int(y1), w, h]
                dets.append((tlwh, float(conf), 'person'))
                person_detections.append((tlwh, float(conf), label))
                area = w * h
                if config.AUTO_SELECT_SMALLEST and (smallest_area is None or area < smallest_area):
                    smallest_area = area
                    smallest_det_tlwh = tlwh

        # Ensure cached bed appears in outputs
        if self.cached_bed_box is not None:
            if not any(det['class'] == 'bed' for det in all_detections):
                all_detections.append({
                    'bbox': self.cached_bed_box,
                    'class': 'bed',
                    'confidence': 0.95
                })

        return dets, self.cached_bed_box, all_detections, person_detections, smallest_det_tlwh

    def reset_bed_cache(self):
        self.cached_bed_box = None
        self.bed_detection_frames = 0
        self.frames_since_bed_detection = 0
        print("[BED] Cache reset")

    def get_bed_status(self):
        return {
            'cached': self.cached_bed_box is not None,
            'bed_box': self.cached_bed_box,
            'frames_confirmed': self.bed_detection_frames,
            'frames_since_detection': self.frames_since_bed_detection,
            'last_inference_ms': self.last_inference_ms
        }
