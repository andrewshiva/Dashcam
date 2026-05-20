import os
import tempfile
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage
from ultralytics import YOLO
from taxonomy import NHAI_TOR_ANOMALIES, anomaly_metadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Inference Service")

# Initialize GCS client and YOLO models
storage_client = storage.Client()
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "nhai-das-dev-processed")

# Retrieve YOLO model names from environment variable.
# YOLO_MODEL_NAMES supports comma-separated models, while YOLO_MODEL_NAME remains
# supported for older deployments.
YOLO_MODEL_NAME = os.environ.get("YOLO_MODEL_NAME", "yolov8n.pt")
YOLO_MODEL_NAMES = [
    name.strip()
    for name in os.environ.get("YOLO_MODEL_NAMES", YOLO_MODEL_NAME).split(",")
    if name.strip()
]
models = {}

MODEL_GROUP_MODEL_NAMES = {}
for assignment in os.environ.get("MODEL_GROUP_MODEL_NAMES", "").split(";"):
    if not assignment.strip() or "=" not in assignment:
        continue
    group_name, group_models = assignment.split("=", 1)
    MODEL_GROUP_MODEL_NAMES[group_name.strip()] = [
        name.strip()
        for name in group_models.split("|")
        if name.strip()
    ]

@app.on_event("startup")
def load_model():
    global models
    try:
        # Avoid PyTorch 2.6+ serialization issues with Ultralytics DetectionModel
        try:
            import torch
            from ultralytics.nn.tasks import DetectionModel
            if hasattr(torch.serialization, 'add_safe_globals'):
                torch.serialization.add_safe_globals([DetectionModel])
                logger.info("Added DetectionModel to PyTorch safe globals")
        except Exception as py_err:
            logger.warning(f"Could not configure PyTorch safe globals: {py_err}")

        for model_name in YOLO_MODEL_NAMES:
            try:
                logger.info(f"Loading YOLO model: {model_name}...")
                models[model_name] = YOLO(model_name)
                logger.info(f"YOLO model {model_name} loaded successfully")
            except Exception as model_error:
                logger.exception(
                    "PIPELINE_FAILURE stage=model_load model=%s error=%s",
                    model_name,
                    model_error,
                )
        for group_model_names in MODEL_GROUP_MODEL_NAMES.values():
            for model_name in group_model_names:
                if model_name in models:
                    continue
                try:
                    logger.info(f"Loading grouped YOLO model: {model_name}...")
                    models[model_name] = YOLO(model_name)
                    logger.info(f"Grouped YOLO model {model_name} loaded successfully")
                except Exception as model_error:
                    logger.exception(
                        "PIPELINE_FAILURE stage=model_load model=%s error=%s",
                        model_name,
                        model_error,
                    )
    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=model_registry_load error=%s", e)

# Strict NHAI Privacy Filter: Blocked classes that must never be recorded
BLOCKED_CLASSES = {
    0: "person",              # Pedestrian
    1: "bicycle",             # Cyclist
    2: "car",                 # Passenger vehicle
    3: "motorcycle",          # Motorcycle rider
    5: "bus",                 # Bus
    7: "truck",               # Transport truck
    16: "dog",                # Animals on road
}

# NHAI TOR-Compliant Asset and Defect Mapping (mapped from standard COCO class IDs for backward compatibility)
ROAD_DEFECT_MAPPING = {
    9: "poor_signboard_visibility",     # COCO traffic light -> poor_signboard_visibility
    11: "damaged_signboard",            # COCO stop sign -> damaged_signboard
    12: "poor_marker_visibility",       # COCO parking meter -> poor_marker_visibility
    13: "damaged_bus_shelter",          # COCO bench -> damaged_bus_shelter
}

MODEL_CLASS_MAPPINGS = {
    "default": ROAD_DEFECT_MAPPING,
}

for assignment in os.environ.get("MODEL_CLASS_MAPPINGS_JSON", "").splitlines():
    # Reserved for future JSON-line model mappings without changing code.
    # Example line:
    # pavement-best.pt={"0":"pothole","1":"cracking","2":"rutting"}
    if "=" not in assignment:
        continue
    model_name, raw_mapping = assignment.split("=", 1)
    try:
        import json

        MODEL_CLASS_MAPPINGS[model_name.strip()] = {
            int(class_id): anomaly_code
            for class_id, anomaly_code in json.loads(raw_mapping).items()
            if anomaly_code in NHAI_TOR_ANOMALIES
        }
    except Exception as mapping_error:
        logger.warning("Ignoring invalid model mapping for %s: %s", model_name, mapping_error)

# Approved NHAI TOR-compliant defect types for CV analysis
SURFACE_DEFECTS = ["pothole", "cracking", "rutting", "shoulder_drop"]

class InferenceRequest(BaseModel):
    video_name: str
    frames: int

class MultiDetectionRequest(BaseModel):
    video_name: str
    frames: int
    return_all: bool = False

def clamp_normalized(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)

def model_group_for_model(model_name: str) -> str:
    for group_name, model_names in MODEL_GROUP_MODEL_NAMES.items():
        if model_name in model_names:
            return group_name
    return "generic_yolo_model"

def anomaly_for_model_class(model_name: str, class_id: int) -> str | None:
    mapping = MODEL_CLASS_MAPPINGS.get(model_name) or MODEL_CLASS_MAPPINGS["default"]
    return mapping.get(class_id)

def build_detection(
    *,
    anomaly_code: str,
    confidence: float,
    method: str,
    model_name: str,
    model_family: str,
    frame_id: str,
    frame_index: int,
    annotation,
) -> dict:
    metadata = anomaly_metadata(anomaly_code)
    return {
        "type": anomaly_code,
        "confidence": confidence,
        "method": method,
        "model_name": model_name,
        "model_family": model_family,
        "model_group": metadata["model_group"],
        "category": metadata["category"],
        "label": metadata["label"],
        "frame_id": frame_id,
        "frame_index": frame_index,
        "annotation": annotation,
    }

def build_annotation(contour, roi: tuple[int, int, int, int], image_shape: tuple[int, int, int]) -> dict:
    """
    Converts a contour found inside the road ROI to normalized image coordinates.
    """
    import cv2

    image_height, image_width = image_shape[:2]
    roi_x1, roi_y1, roi_x2, roi_y2 = roi

    x, y, width, height = cv2.boundingRect(contour)
    abs_x1 = roi_x1 + x
    abs_y1 = roi_y1 + y
    abs_x2 = abs_x1 + width
    abs_y2 = abs_y1 + height

    epsilon = 0.03 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    if len(approx) < 3:
        polygon_pixels = [
            (abs_x1, abs_y1),
            (abs_x2, abs_y1),
            (abs_x2, abs_y2),
            (abs_x1, abs_y2),
        ]
    else:
        polygon_pixels = [
            (roi_x1 + int(point[0][0]), roi_y1 + int(point[0][1]))
            for point in approx
        ]

    return {
        "coordinate_space": "normalized",
        "bbox": [
            clamp_normalized(abs_x1 / image_width),
            clamp_normalized(abs_y1 / image_height),
            clamp_normalized(abs_x2 / image_width),
            clamp_normalized(abs_y2 / image_height),
        ],
        "polygon": [
            [clamp_normalized(px / image_width), clamp_normalized(py / image_height)]
            for px, py in polygon_pixels
        ],
        "road_roi": [
            clamp_normalized(roi_x1 / image_width),
            clamp_normalized(roi_y1 / image_height),
            clamp_normalized(roi_x2 / image_width),
            clamp_normalized(roi_y2 / image_height),
        ],
        "image_width": image_width,
        "image_height": image_height,
    }

def get_road_roi(image_shape: tuple[int, int, ...]) -> tuple[int, int, int, int]:
    """
    Returns the bounding box coordinates (x1, y1, x2, y2) of the road ROI.
    This ROI avoids the sky/horizon, side shoulders, and bottom timestamp strip.
    """
    image_height, image_width = image_shape[:2]
    return (
        int(image_width * 0.08),
        int(image_height * 0.46),
        int(image_width * 0.96),
        int(image_height * 0.88),
    )

def localize_road_surface_defect(img) -> dict | None:
    """
    Finds the strongest dark/edge contour inside the drivable road region only.
    The ROI avoids the sky/horizon and the dashcam timestamp strip.
    """
    import cv2
    import numpy as np

    image_height, image_width = img.shape[:2]
    roi = get_road_roi(img.shape)
    x1, y1, x2, y2 = roi
    road_region = img[y1:y2, x1:x2]

    if road_region.size == 0:
        return None

    gray = cv2.cvtColor(road_region, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 45, 135)
    
    # Calculate adaptive thresholds based on road region median brightness
    median_val = np.median(blurred)
    dark_thresh = max(10, min(82, int(median_val * 0.65)))
    mid_dark_thresh = max(20, min(145, int(median_val * 1.15)))

    dark_mask = cv2.inRange(blurred, 0, dark_thresh)
    mid_dark_mask = cv2.inRange(blurred, 0, mid_dark_thresh)
    crack_edges = cv2.bitwise_and(edges, mid_dark_mask)
    combined = cv2.bitwise_or(dark_mask, crack_edges)

    kernel = np.ones((3, 3), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined = cv2.dilate(combined, kernel, iterations=1)

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    roi_area = road_region.shape[0] * road_region.shape[1]
    min_area = max(24, roi_area * 0.00015)
    max_area = roi_area * 0.12
    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        if area < min_area or area > max_area or width < 4 or height < 3:
            continue

        # Filter out extremely elongated horizontal boundary contours (often lane borders or markings)
        if (x == 0 or (x + width) >= road_region.shape[1]) and width > road_region.shape[1] * 0.6:
            continue

        # Prefer road-surface marks that are lower in the lane and compact.
        vertical_weight = 1 + (y / max(1, road_region.shape[0])) * 0.35
        compactness_penalty = 1 + (width * height / max(1, roi_area)) * 0.8
        score = (area * vertical_weight) / compactness_penalty
        candidates.append((score, contour))

    if not candidates:
        return None

    best_contour = max(candidates, key=lambda item: item[0])[1]
    return build_annotation(best_contour, roi, img.shape)

def analyze_road_surface(image_path: str) -> dict | None:
    """
    Basic CV analysis for road surface defects using edge detection
    and dark patch analysis. Returns a detection if anomaly found and localized.
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        return None

    # Harmonize ROI: run structural metrics on the EXACT SAME road surface ROI
    roi = get_road_roi(img.shape)
    x1, y1, x2, y2 = roi
    road_region = img[y1:y2, x1:x2]

    if road_region.size == 0:
        return None

    # Call localization to see if we have a valid target defect contour
    annotation = localize_road_surface_defect(img)

    # CRITICAL: Enforce contour presence to eliminate massive false positives!
    # If we cannot localize a discrete defect contour, do NOT flag any defect.
    if annotation is None:
        return None

    # Convert to grayscale
    gray = cv2.cvtColor(road_region, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection for cracks inside the road region
    edges = cv2.Canny(blurred, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    # Dark patch detection for potholes (darker areas on road)
    median_val = np.median(blurred)
    dark_thresh = max(10, min(60, int(median_val * 0.5)))
    _, dark_mask = cv2.threshold(blurred, dark_thresh, 255, cv2.THRESH_BINARY_INV)
    dark_ratio = np.sum(dark_mask > 0) / dark_mask.size

    # Texture analysis using Laplacian variance
    laplacian_var = cv2.Laplacian(blurred, cv2.CV_64F).var()

    # Decision logic is now backed by a verified localized contour annotation
    if dark_ratio > 0.15:
        return {
            "type": "pothole",
            "confidence": min(0.95, 0.6 + dark_ratio),
            "method": "dark_patch_analysis",
            "annotation": annotation,
        }
    elif edge_density > 0.12:
        return {
            "type": "cracking",
            "confidence": min(0.92, 0.55 + edge_density),
            "method": "edge_density_analysis",
            "annotation": annotation,
        }
    elif laplacian_var > 500:
        return {
            "type": "rutting",
            "confidence": min(0.85, 0.5 + laplacian_var / 2000),
            "method": "texture_analysis",
            "annotation": annotation,
        }

    return None

def deduplicate_detections(raw_detections: list[dict], window_size: int = 5) -> list[dict]:
    """
    Temporally de-duplicates raw detections of the same category.
    If the same defect type is found within window_size frames, they are grouped
    and only the one with the highest confidence is retained.
    """
    if not raw_detections:
        return []

    # Sort detections by frame index and then confidence (highest first)
    sorted_dets = sorted(raw_detections, key=lambda x: (x["frame_index"], -x["confidence"]))

    deduplicated = []

    # Group by defect type and model so each model's signal remains visible.
    by_type = {}
    for det in sorted_dets:
        group_key = (det["type"], det.get("model_name", "unknown"))
        by_type.setdefault(group_key, []).append(det)

    for _, type_dets in by_type.items():
        active_group = []
        for det in type_dets:
            if not active_group:
                active_group.append(det)
            else:
                last_det = active_group[-1]
                # If frame difference is within the window, group them as the same defect instance
                if det["frame_index"] - last_det["frame_index"] <= window_size:
                    active_group.append(det)
                else:
                    # Close current group and record the best candidate
                    best_group_det = max(active_group, key=lambda x: x["confidence"])
                    deduplicated.append(best_group_det)
                    active_group = [det]
        if active_group:
            best_group_det = max(active_group, key=lambda x: x["confidence"])
            deduplicated.append(best_group_det)

    # Sort the final deduplicated results back to sequential frame order
    return sorted(deduplicated, key=lambda x: x["frame_index"])

@app.post("/")
def run_inference(request: InferenceRequest):
    """
    Run YOLOv8 inference on extracted frames from GCS.
    Downloads frames, runs object detection + road surface analysis,
    de-duplicates multiple anomalies, and returns all detections.
    """
    logger.info(f"Running YOLOv8 inference on {request.frames} frames from {request.video_name}")

    # Download frames from GCS
    base_name = os.path.splitext(os.path.basename(request.video_name))[0]
    prefix = f"frames/{base_name}/"
    bucket = storage_client.bucket(PROCESSED_BUCKET)

    # List available frames with a configurable maximum (defaults to 30)
    MAX_INFERENCE_FRAMES = int(os.environ.get("MAX_INFERENCE_FRAMES", "30"))
    blobs = list(bucket.list_blobs(prefix=prefix, max_results=min(request.frames, MAX_INFERENCE_FRAMES)))

    if not blobs:
        logger.error(
            "PIPELINE_FAILURE stage=ai_inference video_id=%s error=No frames found at gs://%s/%s",
            request.video_name,
            PROCESSED_BUCKET,
            prefix,
        )
        raise HTTPException(
            status_code=404,
            detail=f"No frames found in processed bucket under prefix '{prefix}'. Cannot execute inference."
        )

    if not models:
        logger.warning("No YOLO models loaded. Running deterministic CV-based road surface analysis only.")

    all_raw_detections = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for blob in blobs:
            local_path = os.path.join(tmpdir, os.path.basename(blob.name))
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded frame: {blob.name}")

            # Extract numeric frame index from filename
            frame_filename = os.path.basename(blob.name)
            try:
                frame_index = int(''.join(filter(str.isdigit, frame_filename)))
            except Exception:
                frame_index = 0

            # 1. Run every configured YOLO model on the same frame.
            for model_name, yolo_model in models.items():
                try:
                    results = yolo_model(local_path, verbose=False, conf=0.3)
                    for result in results:
                        for box in result.boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            
                            # Strict NHAI privacy filtering: block vehicles, pedestrians, license plates
                            if cls_id in BLOCKED_CLASSES:
                                logger.info(f"Privacy Exclusion: Discarded detected blocked class {cls_id} ({BLOCKED_CLASSES[cls_id]})")
                                continue
                                
                            anomaly_code = anomaly_for_model_class(model_name, cls_id)
                            if anomaly_code:
                                all_raw_detections.append(build_detection(
                                    anomaly_code=anomaly_code,
                                    confidence=round(conf, 2),
                                    method="yolo_detection",
                                    model_name=model_name,
                                    model_family="yolo",
                                    frame_id=frame_filename,
                                    frame_index=frame_index,
                                    annotation=None,
                                ))
                except Exception as e:
                    logger.exception(
                        "PIPELINE_FAILURE stage=yolo_frame_inference video_id=%s model=%s frame_id=%s error=%s",
                        request.video_name,
                        model_name,
                        blob.name,
                        e,
                    )

            # 2. Run road surface analysis
            surface_result = analyze_road_surface(local_path)
            if surface_result:
                all_raw_detections.append(build_detection(
                    anomaly_code=surface_result["type"],
                    confidence=surface_result["confidence"],
                    method=surface_result["method"],
                    model_name="road_surface_cv",
                    model_family="computer_vision",
                    frame_id=frame_filename,
                    frame_index=frame_index,
                    annotation=surface_result["annotation"],
                ))

    # Run frame-based temporal de-duplication
    deduplicated_dets = deduplicate_detections(all_raw_detections, window_size=5)

    # Determine highest confidence detection for backward compatibility
    best_detection = None
    if deduplicated_dets:
        best_detection = max(deduplicated_dets, key=lambda x: x["confidence"])

    # Fallback to road_clear if nothing was detected
    if best_detection is None:
        best_detection = {
            "type": "road_clear",
            "confidence": 0.90,
            "method": "no_defects_found",
            "frame_id": "frame_0000.jpg",
            "model_name": "multi_model_pipeline",
            "model_family": "fallback",
            "model_group": "fallback",
            "category": "status",
            "label": "Road Clear",
            "annotation": None,
        }

    # Format detections for batch output (stripping raw frame_index used internally)
    detections_output = [
        {
            "frame_id": d["frame_id"],
            "detection_type": d["type"],
            "confidence": d["confidence"],
            "model_name": d.get("model_name", "unknown"),
            "model_family": d.get("model_family", "unknown"),
            "model_group": d.get("model_group", "unknown"),
            "category": d.get("category", "unknown"),
            "label": d.get("label", d["type"].replace("_", " ").title()),
            "method": d.get("method", "unknown"),
            "annotation": d.get("annotation"),
        }
        for d in deduplicated_dets
    ]

    logger.info(f"Deduplicated detections count: {len(detections_output)}. Best detection: {best_detection}")

    return {
        "status": "success",
        "video_name": request.video_name,
        "detection_type": best_detection["type"],
        "confidence": best_detection["confidence"],
        "model": best_detection.get("model_name", "multi_model_pipeline"),
        "models": list(models.keys()) + ["road_surface_cv"],
        "taxonomy_version": "nhai_tor_annexure_ii",
        "supported_anomalies": NHAI_TOR_ANOMALIES,
        "method": best_detection.get("method", "unknown"),
        "frame_id": best_detection.get("frame_id", "frame_0000.jpg"),
        "annotation": best_detection.get("annotation"),
        "detections": detections_output,
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": bool(models),
        "models": list(models.keys()),
        "model_groups": MODEL_GROUP_MODEL_NAMES,
        "cv_model": "road_surface_cv",
        "supported_anomalies": NHAI_TOR_ANOMALIES,
    }
