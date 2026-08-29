import os
import tempfile
import cv2
import logging
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Slicing and Frame Extractor Service")

storage_client = storage.Client()
PROCESSED_BUCKET_NAME = os.environ.get("PROCESSED_BUCKET", "nhai-das-dev-processed")

class PubSubMessage(BaseModel):
    message: dict

@app.post("/")
async def process_video_event(request: Request):
    """
    Handles Eventarc (Pub/Sub) push events when a new video lands in the validated bucket.
    """
    file_name = "unknown"
    temp_video_path = None
    try:
        body = await request.json()
        logger.info(f"Received event: {body}")
        
        # Extract bucket and file name from the event
        # Depending on Eventarc configuration, the payload might be in 'message.data' base64 encoded
        # For simplicity, assuming a direct HTTP invocation or standard Cloud Storage PubSub notification
        if "message" in body and "data" in body["message"]:
            import base64
            import json
            data = base64.b64decode(body["message"]["data"]).decode("utf-8")
            event_data = json.loads(data)
        else:
            event_data = body

        source_bucket_name = event_data.get("bucket")
        file_name = event_data.get("name")

        if not source_bucket_name or not file_name:
            raise ValueError("Invalid event data. Missing bucket or file name.")

        logger.info(f"Processing video {file_name} from bucket {source_bucket_name}")
        
        # Download the video locally
        source_bucket = storage_client.bucket(source_bucket_name)
        blob = source_bucket.blob(file_name)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            blob.download_to_filename(temp_video.name)
            temp_video_path = temp_video.name
            
        logger.info(f"Downloaded video to {temp_video_path}")

        # Extract frames (1 frame per second as a default strategy)
        extracted_frames = extract_frames(temp_video_path, file_name)

        logger.info(f"Successfully processed {file_name}. Extracted {len(extracted_frames)} frames.")
        return {"status": "success", "frames_extracted": len(extracted_frames)}

    except Exception as e:
        logger.exception(
            "PIPELINE_FAILURE stage=frame_extraction video_id=%s error=%s",
            file_name,
            e,
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)

def extract_frames(video_path: str, original_file_name: str) -> list:
    """
    Extracts 1 frame per second from the video and uploads to GCS.
    """
    frames = []
    processed_bucket = storage_client.bucket(PROCESSED_BUCKET_NAME)
    
    # Remove extension from original file name for folder structure
    base_name = os.path.splitext(os.path.basename(original_file_name))[0]

    vidcap = cv2.VideoCapture(video_path)
    if not vidcap.isOpened():
        raise RuntimeError("OpenCV could not open the video file")

    fps = vidcap.get(cv2.CAP_PROP_FPS)
    
    if fps == 0 or not fps:
        fps = 30 # fallback
    frame_interval = max(1, int(round(fps)))
        
    logger.info(f"Video FPS: {fps}")
    
    success, image = vidcap.read()
    count = 0
    frame_count = 0

    while success:
        # Extract 1 frame per second
        if count % frame_interval == 0:
            # Save frame to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_frame:
                temp_frame_path = temp_frame.name
                cv2.imwrite(temp_frame.name, image)
                
                # Upload to GCS
                destination_blob_name = f"frames/{base_name}/frame_{frame_count:04d}.jpg"
                blob = processed_bucket.blob(destination_blob_name)
            try:
                blob.upload_from_filename(temp_frame_path)
                
                frames.append(destination_blob_name)
                frame_count += 1
            finally:
                os.remove(temp_frame_path)
            
        success, image = vidcap.read()
        count += 1
        
    vidcap.release()
    if not frames:
        raise RuntimeError("No frames were extracted from the video")

    return frames
