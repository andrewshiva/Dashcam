import os
import tempfile
import logging
import json
import base64
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from google.cloud import storage
from google.cloud.workflows import executions_v1
from google.cloud.workflows.executions_v1 import Execution
import ffmpeg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NHAI Video Validation Service")

# Environment variables
VALIDATED_BUCKET = os.environ.get("VALIDATED_BUCKET", "nhai-das-dev-validated-video")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET", "nhai-das-dev-quarantine")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "peppy-castle-276303")
GCP_REGION = os.environ.get("GCP_REGION", "asia-south1")
WORKFLOW_NAME = os.environ.get("WORKFLOW_NAME", "nhai-das-pipeline")

# Initialize GCP Storage Client
storage_client = storage.Client()
workflow_client = executions_v1.ExecutionsClient()

def validate_video(file_path: str) -> tuple[bool, str]:
    """
    Validates a video file using ffprobe.
    Returns (is_valid, reason_if_invalid)
    """
    try:
        # Probe the video file using ffmpeg-python
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream is None:
            return False, "No video stream found in file"
            
        # 1. Check Codec
        codec = video_stream.get('codec_name')
        if codec not in ['h264', 'hevc', 'h265']:
            return False, f"Unsupported codec: {codec}. Required: h264 or h265."
            
        # 2. Check Resolution (e.g., minimum 720p)
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        if width < 640 or height < 360:
            return False, f"Resolution too low: {width}x{height}. Minimum required: 640x360."
            
        # 3. Check Duration (Optional: e.g., minimum 5 seconds)
        duration = float(probe['format'].get('duration', 0))
        if duration < 5.0:
            return False, f"Video too short: {duration}s. Minimum required: 5s."

        return True, "Valid"
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg probe error: {e.stderr.decode('utf8')}")
        return False, "File is corrupt or unreadable by FFmpeg"
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False, f"Unexpected validation error: {str(e)}"

def copy_blob(bucket_name: str, blob_name: str, destination_bucket_name: str):
    """Copies a blob from one bucket to another."""
    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(blob_name)
    destination_bucket = storage_client.bucket(destination_bucket_name)

    logger.info(f"Copying {blob_name} to {destination_bucket_name}")
    
    return source_bucket.copy_blob(
        source_blob, destination_bucket, blob_name
    )

def delete_blob(bucket_name: str, blob_name: str):
    """Deletes a blob after downstream work has been safely started."""
    storage_client.bucket(bucket_name).delete_blob(blob_name)

def move_blob(bucket_name: str, blob_name: str, destination_bucket_name: str):
    """Moves a blob from one bucket to another."""
    blob_copy = copy_blob(bucket_name, blob_name, destination_bucket_name)

    # Delete the original
    delete_blob(bucket_name, blob_name)
    
    return blob_copy

def start_pipeline_workflow(bucket_name: str, file_name: str) -> dict:
    """Starts the Cloud Workflow that runs the processing pipeline."""
    parent = workflow_client.workflow_path(GCP_PROJECT, GCP_REGION, WORKFLOW_NAME)
    argument = {
        "bucket": bucket_name,
        "name": file_name,
        "source": "video-validator",
    }
    execution = workflow_client.create_execution(
        parent=parent,
        execution=Execution(argument=json.dumps(argument)),
    )
    execution_id = execution.name.split("/")[-1]
    logger.info(
        "Started workflow execution %s for gs://%s/%s",
        execution_id,
        bucket_name,
        file_name,
    )
    return {"execution_id": execution_id, "execution_name": execution.name}

def extract_storage_event(body: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes Eventarc and Pub/Sub Cloud Storage notifications."""
    message = body.get("message")
    if isinstance(message, dict):
        encoded_data = message.get("data")
        if encoded_data:
            try:
                decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                return json.loads(decoded_data)
            except (ValueError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid Pub/Sub storage notification payload: {e}") from e

        attributes = message.get("attributes") or {}
        bucket_id = attributes.get("bucketId") or attributes.get("bucket")
        object_id = attributes.get("objectId") or attributes.get("name")
        if bucket_id and object_id:
            return {"bucket": bucket_id, "name": object_id}

    event_data = body.get("data")
    if isinstance(event_data, dict):
        return event_data

    return body

@app.post("/")
async def handle_eventarc_trigger(request: Request):
    """
    Endpoint that handles Eventarc or Pub/Sub push messages from GCS object.finalize events.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        event_data = extract_storage_event(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Cloud Storage 'object.finalize' event data has 'bucket' and 'name'
    bucket_name = event_data.get("bucket")
    file_name = event_data.get("name")

    if not bucket_name or not file_name:
        logger.warning(f"Ignored event: missing bucket or name in body: {event_data}")
        # Return 200 so invalid storage notifications do not retry forever.
        return {"status": "ignored", "reason": "Not a valid GCS event"}

    logger.info(f"Processing new video: gs://{bucket_name}/{file_name}")

    # Ensure it's a video file type before downloading
    if not file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        logger.info(f"File {file_name} is not a video. Moving to quarantine.")
        move_blob(bucket_name, file_name, QUARANTINE_BUCKET)
        return {"status": "quarantined", "reason": "Not a video file extension"}

    # Download file to ephemeral storage for validation
    source_bucket = storage_client.bucket(bucket_name)
    blob = source_bucket.blob(file_name)
    
    temp_fd, temp_local_filename = tempfile.mkstemp()
    os.close(temp_fd)
    
    try:
        logger.info(f"Downloading {file_name} to {temp_local_filename}")
        blob.download_to_filename(temp_local_filename)
        
        # Run Validation
        logger.info(f"Validating {file_name}")
        is_valid, reason = validate_video(temp_local_filename)
        
        if is_valid:
            logger.info(f"Validation SUCCESS for {file_name}")
            copy_blob(bucket_name, file_name, VALIDATED_BUCKET)
            try:
                workflow_info = start_pipeline_workflow(VALIDATED_BUCKET, file_name)
            except Exception as workflow_error:
                logger.error(
                    "PIPELINE_FAILURE stage=workflow_start video_id=%s error=%s",
                    file_name,
                    workflow_error,
                )
                try:
                    delete_blob(VALIDATED_BUCKET, file_name)
                except Exception as cleanup_error:
                    logger.warning(
                        "Could not remove validated copy %s after workflow start failure: %s",
                        file_name,
                        cleanup_error,
                    )
                raise
            try:
                delete_blob(bucket_name, file_name)
            except Exception as cleanup_error:
                logger.warning(
                    "Workflow started but raw object cleanup failed for %s: %s",
                    file_name,
                    cleanup_error,
                )
            result = "validated"
        else:
            logger.warning(f"Validation FAILED for {file_name}. Reason: {reason}")
            move_blob(bucket_name, file_name, QUARANTINE_BUCKET)
            workflow_info = None
            
            # Optionally: write a report file explaining why it failed
            report_blob = storage_client.bucket(QUARANTINE_BUCKET).blob(f"{file_name}.report.txt")
            report_blob.upload_from_string(f"Validation Failed.\nReason: {reason}")
            result = "quarantined"

    except Exception as e:
        logger.exception(
            "PIPELINE_FAILURE stage=validation video_id=%s error=%s",
            file_name,
            e,
        )
        # Try to move to quarantine on processing failure
        try:
            move_blob(bucket_name, file_name, QUARANTINE_BUCKET)
        except Exception as quarantine_error:
            logger.warning(
                "Could not quarantine %s after processing failure: %s",
                file_name,
                quarantine_error,
            )
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up local file
        if os.path.exists(temp_local_filename):
            os.remove(temp_local_filename)

    return {
        "file": file_name,
        "status": result,
        "reason": reason if not is_valid else "OK",
        "workflow": workflow_info if is_valid else None,
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
