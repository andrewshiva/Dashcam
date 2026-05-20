import os
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
from google.cloud.workflows import executions_v1
from google.cloud.workflows.executions_v1 import Execution
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NHAI Dashcam Dashboard API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "nhaidb")

def build_database_url() -> str:
    user = quote_plus(DB_USER)
    password = quote_plus(DB_PASSWORD)
    database = quote_plus(DB_NAME)
    if DB_HOST.startswith("/"):
        return f"postgresql+asyncpg://{user}:{password}@/{database}?host={quote_plus(DB_HOST)}"
    return f"postgresql+asyncpg://{user}:{password}@{DB_HOST}/{database}"

DATABASE_URL = build_database_url()

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# GCS + Workflow configuration
GCS_RAW_BUCKET = os.environ.get("RAW_BUCKET", "nhai-das-dev-raw-video")
GCS_VALIDATED_BUCKET = os.environ.get("VALIDATED_BUCKET", "nhai-das-dev-validated-video")
GCS_QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET", "nhai-das-dev-quarantine")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "peppy-castle-276303")
GCP_REGION = os.environ.get("GCP_REGION", "asia-south1")
WORKFLOW_NAME = os.environ.get("WORKFLOW_NAME", "nhai-das-pipeline")
MAX_PIPELINE_ACTIVE_SECONDS = int(os.environ.get("MAX_PIPELINE_ACTIVE_SECONDS", "3600"))
MAX_STAGE_IDLE_SECONDS = int(os.environ.get("MAX_STAGE_IDLE_SECONDS", "900"))

storage_client = storage.Client()

ALLOWED_VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv')
VIDEO_UPLOADS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS video_uploads (
        id BIGSERIAL PRIMARY KEY,
        original_filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL UNIQUE,
        raw_bucket TEXT NOT NULL,
        raw_object_name TEXT NOT NULL,
        raw_video_gcs_uri TEXT NOT NULL,
        content_type TEXT,
        size_bytes BIGINT,
        gcs_generation TEXT,
        gcs_metageneration TEXT,
        crc32c TEXT,
        md5_hash TEXT,
        status TEXT NOT NULL DEFAULT 'stored',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""

VIDEO_UPLOADS_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_video_uploads_stored_filename
    ON video_uploads (stored_filename)
"""

PIPELINE_EVENTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS pipeline_events (
        id BIGSERIAL PRIMARY KEY,
        video_id TEXT NOT NULL,
        execution_id TEXT,
        stage TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        details JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""

PIPELINE_EVENTS_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_pipeline_events_video_id_created_at
    ON pipeline_events (video_id, created_at DESC)
"""

async def get_db():
    async with async_session() as session:
        yield session

@app.on_event("startup")
async def ensure_operational_tables():
    try:
        async with async_session() as session:
            await session.execute(text(VIDEO_UPLOADS_TABLE_SQL))
            await session.execute(text(VIDEO_UPLOADS_INDEX_SQL))
            await session.execute(text(PIPELINE_EVENTS_TABLE_SQL))
            await session.execute(text(PIPELINE_EVENTS_INDEX_SQL))
            await session.commit()
    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=dashboard_api_startup error=%s", e)
        raise



class DefectResponse(BaseModel):
    id: str
    type: str
    confidence: float
    latitude: float
    longitude: float
    timestamp: str
    video_id: Optional[str] = None
    frame_id: Optional[str] = None
    model_name: Optional[str] = None
    model_family: Optional[str] = None
    model_group: Optional[str] = None
    category: Optional[str] = None
    label: Optional[str] = None
    method: Optional[str] = None
    annotation: Optional[Dict[str, Any]] = None

def sanitize_video_filename(filename: str) -> str:
    original = os.path.basename(filename or "video.mp4")
    stem, ext = os.path.splitext(original)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_")
    safe_stem = safe_stem[:80] or "video"
    safe_ext = ext.lower()
    return f"{safe_stem}{safe_ext}"

def create_stored_video_name(filename: str) -> str:
    safe_filename = sanitize_video_filename(filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique_suffix = uuid.uuid4().hex[:10]
    return f"{timestamp}-{unique_suffix}-{safe_filename}"

def get_gcs_uri(bucket: str, object_name: str) -> str:
    return f"gs://{bucket}/{object_name}"

async def get_upload_size(file: UploadFile) -> Optional[int]:
    if file.size is not None:
        return file.size

    try:
        current_position = file.file.tell()
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(current_position)
        return size
    except Exception:
        return None

async def record_video_upload(
    *,
    original_filename: str,
    stored_filename: str,
    content_type: str,
    size_bytes: Optional[int],
    blob: Any,
):
    async with async_session() as session:
        await session.execute(
            text("""
                INSERT INTO video_uploads (
                    original_filename,
                    stored_filename,
                    raw_bucket,
                    raw_object_name,
                    raw_video_gcs_uri,
                    content_type,
                    size_bytes,
                    gcs_generation,
                    gcs_metageneration,
                    crc32c,
                    md5_hash,
                    status,
                    updated_at
                )
                VALUES (
                    :original_filename,
                    :stored_filename,
                    :raw_bucket,
                    :raw_object_name,
                    :raw_video_gcs_uri,
                    :content_type,
                    :size_bytes,
                    :gcs_generation,
                    :gcs_metageneration,
                    :crc32c,
                    :md5_hash,
                    'stored',
                    NOW()
                )
                ON CONFLICT (stored_filename) DO UPDATE SET
                    status = EXCLUDED.status,
                    gcs_generation = EXCLUDED.gcs_generation,
                    gcs_metageneration = EXCLUDED.gcs_metageneration,
                    crc32c = EXCLUDED.crc32c,
                    md5_hash = EXCLUDED.md5_hash,
                    updated_at = NOW()
            """),
            {
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "raw_bucket": blob.bucket.name if (blob and hasattr(blob, "bucket") and blob.bucket) else GCS_VALIDATED_BUCKET,
                "raw_object_name": stored_filename,
                "raw_video_gcs_uri": get_gcs_uri(blob.bucket.name if (blob and hasattr(blob, "bucket") and blob.bucket) else GCS_VALIDATED_BUCKET, stored_filename),
                "content_type": content_type,
                "size_bytes": size_bytes,
                "gcs_generation": str(blob.generation) if blob.generation else None,
                "gcs_metageneration": str(blob.metageneration) if blob.metageneration else None,
                "crc32c": blob.crc32c,
                "md5_hash": blob.md5_hash,
            },
        )
        await session.commit()

async def update_video_upload_status(stored_filename: str, status: str):
    async with async_session() as session:
        await session.execute(
            text("""
                UPDATE video_uploads
                SET status = :status, updated_at = NOW()
                WHERE stored_filename = :stored_filename
            """),
            {"stored_filename": stored_filename, "status": status},
        )
        await session.commit()

async def get_video_upload_record(stored_filename: str) -> Optional[Dict[str, Any]]:
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    original_filename,
                    stored_filename,
                    raw_bucket,
                    raw_object_name,
                    raw_video_gcs_uri,
                    content_type,
                    size_bytes,
                    gcs_generation,
                    gcs_metageneration,
                    crc32c,
                    md5_hash,
                    status,
                    created_at,
                    updated_at
                FROM video_uploads
                WHERE stored_filename = :stored_filename
            """),
            {"stored_filename": stored_filename},
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def get_pipeline_events(video_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    video_id,
                    execution_id,
                    stage,
                    status,
                    message,
                    details,
                    created_at
                FROM pipeline_events
                WHERE video_id = :video_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"video_id": video_id, "limit": limit},
        )
        events = []
        for row in result.mappings().all():
            event = dict(row)
            if isinstance(event.get("details"), str):
                try:
                    event["details"] = json.loads(event["details"])
                except json.JSONDecodeError:
                    event["details"] = None
            if event.get("created_at"):
                event["created_at"] = str(event["created_at"])
            events.append(event)
        return events

def latest_pipeline_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return events[0] if events else None

def status_payload(
    *,
    execution_id: str,
    state: str,
    result: Any = None,
    error: Optional[str] = None,
    storage: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
    workflow_execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "execution_id": execution_id,
        "workflow_execution_id": workflow_execution_id,
        "state": state,
        "result": result,
        "error": error,
        "storage": storage,
        "latest_event": latest_pipeline_event(events or []),
        "events": events or [],
    }

def parse_optional_json(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def parse_datetime_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def seconds_since(value: Any) -> Optional[float]:
    parsed = parse_datetime_value(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()

def detect_pipeline_timeout(
    upload_record: Optional[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> Optional[str]:
    latest_event = latest_pipeline_event(events)
    latest_status = str(latest_event.get("status", "")).upper() if latest_event else ""

    if latest_status in {"FAILED", "SUCCEEDED"}:
        return None

    latest_event_age = seconds_since(latest_event.get("created_at")) if latest_event else None
    if latest_event and latest_event_age is not None and latest_event_age > MAX_STAGE_IDLE_SECONDS:
        return (
            f"Pipeline appears stuck at {latest_event.get('stage')} for "
            f"{int(latest_event_age // 60)} minutes."
        )

    upload_age = seconds_since(upload_record.get("created_at")) if upload_record else None
    if upload_age is not None and upload_age > MAX_PIPELINE_ACTIVE_SECONDS:
        return f"Pipeline exceeded max active time of {MAX_PIPELINE_ACTIVE_SECONDS // 60} minutes."

    return None

def blob_exists(bucket_name: str, object_name: str) -> bool:
    return storage_client.bucket(bucket_name).blob(object_name).exists()

def build_storage_status(stored_filename: str, upload_record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw_exists = blob_exists(GCS_RAW_BUCKET, stored_filename)
    validated_exists = blob_exists(GCS_VALIDATED_BUCKET, stored_filename)
    quarantine_exists = blob_exists(GCS_QUARANTINE_BUCKET, stored_filename)

    return {
        "original_filename": upload_record.get("original_filename") if upload_record else None,
        "stored_filename": stored_filename,
        "raw_gcs_uri": get_gcs_uri(GCS_RAW_BUCKET, stored_filename),
        "validated_gcs_uri": get_gcs_uri(GCS_VALIDATED_BUCKET, stored_filename),
        "quarantine_gcs_uri": get_gcs_uri(GCS_QUARANTINE_BUCKET, stored_filename),
        "raw_exists": raw_exists,
        "validated_exists": validated_exists,
        "quarantine_exists": quarantine_exists,
        "content_type": upload_record.get("content_type") if upload_record else None,
        "size_bytes": upload_record.get("size_bytes") if upload_record else None,
        "status": upload_record.get("status") if upload_record else None,
    }

# ─── Existing Endpoint: Fetch Defects ───────────────────────────────────────

@app.get("/api/v1/defects", response_model=List[DefectResponse])
async def get_defects(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Fetch detected defects from the database with their coordinates.
    """
    query = text("""
        SELECT id, detection_type, confidence, 
               ST_Y(location::geometry) as latitude, 
               ST_X(location::geometry) as longitude, 
               timestamp, video_id, frame_id, metadata
        FROM detections
        WHERE detection_type NOT IN ('vehicle_detected', 'car', 'truck', 'person', 'pedestrian', 'license_plate', 'vehicle')
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    try:
        result = await db.execute(query, {"limit": limit})
        defects = []
        for row in result:
            metadata = row[8] if row[8] else {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            annotation = metadata.get("annotation") if isinstance(metadata, dict) else None
            defects.append({
                "id": str(row[0]),
                "type": row[1],
                "confidence": row[2],
                "latitude": row[3],
                "longitude": row[4],
                "timestamp": str(row[5]),
                "video_id": row[6],
                "frame_id": row[7],
                "model_name": metadata.get("model_name") if isinstance(metadata, dict) else None,
                "model_family": metadata.get("model_family") if isinstance(metadata, dict) else None,
                "model_group": metadata.get("model_group") if isinstance(metadata, dict) else None,
                "category": metadata.get("category") if isinstance(metadata, dict) else None,
                "label": metadata.get("label") if isinstance(metadata, dict) else None,
                "method": metadata.get("method") if isinstance(metadata, dict) else None,
                "annotation": annotation,
            })
        return defects
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=defects_query error=%s", e)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import io

@app.get("/api/v1/defects/{defect_id}/image")
async def get_defect_image(defect_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetches the frame image associated with this defect from GCS and streams it back.
    """
    query = text("SELECT video_id, frame_id FROM detections WHERE id = :id")
    try:
        result = await db.execute(query, {"id": int(defect_id)})
        row = result.fetchone()
        
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="Defect not found")
            
        video_id, frame_id = row[0], row[1]
        if not frame_id:
            frame_id = "frame_0000.jpg"
            
        base_name = os.path.splitext(video_id)[0]
        PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "nhai-das-dev-processed")
        blob_path = f"frames/{base_name}/{frame_id}"
        
        bucket = storage_client.bucket(PROCESSED_BUCKET)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            prefix = f"frames/{base_name}/"
            blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
            if blobs:
                blob = blobs[0]
            else:
                # If no frames in this folder, try video15 as global fallback
                blob = bucket.blob("frames/video15/frame_0000.jpg")
                if not blob.exists():
                    raise HTTPException(status_code=404, detail="No images found for this video")
        
        image_content = blob.download_as_bytes()
        return StreamingResponse(io.BytesIO(image_content), media_type="image/jpeg")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")

# ─── New Endpoint: Upload Video ─────────────────────────────────────────────

@app.post("/api/v1/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Accepts a dashcam video file, streams it to GCS raw bucket, and records
    a durable upload row for status/report tracking.
    The video validation service triggers via Eventarc on GCS finalization,
    which in turn copies the video to validated bucket to trigger the workflow automatically.
    Returns the stored object name as execution_id for status tracking.
    """
    original_filename = os.path.basename(file.filename or "")
    if not original_filename.lower().endswith(ALLOWED_VIDEO_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    stored_filename = create_stored_video_name(original_filename)
    content_type = file.content_type or "video/mp4"
    size_bytes = await get_upload_size(file)

    logger.info(
        "Uploading video: original=%s stored=%s size=%s",
        original_filename,
        stored_filename,
        size_bytes,
    )

    try:
        bucket = storage_client.bucket(GCS_VALIDATED_BUCKET)
        blob = bucket.blob(stored_filename)
        blob.metadata = {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "uploaded_via": "dashboard-api",
        }
        
        await file.seek(0)
        blob.upload_from_file(
            file.file,
            content_type=content_type,
            rewind=True,
            if_generation_match=0,
        )
        blob.reload()

        await record_video_upload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            blob=blob,
        )
        
        logger.info("Stored %s at %s", original_filename, get_gcs_uri(GCS_VALIDATED_BUCKET, stored_filename))

        storage_status = build_storage_status(
            stored_filename,
            {
                "original_filename": original_filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "status": "stored",
            },
        )

        return {
            "status": "success",
            "original_filename": original_filename,
            "filename": stored_filename,
            "stored_filename": stored_filename,
            "bucket": GCS_VALIDATED_BUCKET,
            "gcs_uri": get_gcs_uri(GCS_VALIDATED_BUCKET, stored_filename),
            "execution_id": stored_filename,
            "storage": storage_status,
            "message": "Video stored. Processing initiated."
        }

    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=upload video_id=%s error=%s", original_filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate-upload-url")
async def generate_upload_url(payload: Dict[str, Any]):
    """
    Generates a GCS V4 signed URL for direct client upload of videos of any size.
    """
    from datetime import timedelta
    filename = payload.get("filename")
    content_type = payload.get("content_type", "video/mp4")
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
        
    original_filename = os.path.basename(filename)
    if not original_filename.lower().endswith(ALLOWED_VIDEO_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
        
    stored_filename = create_stored_video_name(original_filename)
    
    try:
        bucket = storage_client.bucket(GCS_VALIDATED_BUCKET)
        blob = bucket.blob(stored_filename)
        
        # Generate GCS Signed URL (valid for 30 minutes)
        try:
            upload_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=30),
                method="PUT",
                content_type=content_type,
            )
        except Exception as sign_err:
            logger.info("Local GCS URL signing failed or not supported (%s). Attempting token-based signing via IAM signBlob.", sign_err)
            try:
                import google.auth
                import google.auth.transport.requests
                
                credentials, _ = google.auth.default()
                auth_request = google.auth.transport.requests.Request()
                credentials.refresh(auth_request)
                
                sa_email = getattr(credentials, "service_account_email", None)
                if not sa_email or sa_email == "default":
                    try:
                        import urllib.request
                        req = urllib.request.Request(
                            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                            headers={"Metadata-Flavor": "Google"}
                        )
                        with urllib.request.urlopen(req, timeout=2) as response:
                            sa_email = response.read().decode("utf-8").strip()
                    except Exception as meta_err:
                        logger.warning("Failed to retrieve service account email from metadata: %s", meta_err)
                
                if not sa_email:
                    raise ValueError("Service account email could not be resolved for IAM token-based signing.")
                    
                logger.info("Signing GCS URL on behalf of service account: %s", sa_email)
                upload_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=30),
                    method="PUT",
                    content_type=content_type,
                    service_account_email=sa_email,
                    access_token=credentials.token,
                )
            except Exception as iam_err:
                logger.exception("Token-based GCS URL signing failed: %s", iam_err)
                raise sign_err
        
        return {
            "status": "success",
            "upload_url": upload_url,
            "stored_filename": stored_filename,
            "gcs_uri": get_gcs_uri(GCS_VALIDATED_BUCKET, stored_filename)
        }
    except Exception as e:
        logger.exception("Failed to generate signed URL: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@app.post("/api/v1/confirm-upload")
async def confirm_upload(payload: Dict[str, Any]):
    """
    Registers the video in the database after successful client-side GCS direct upload.
    """
    original_filename = payload.get("original_filename")
    stored_filename = payload.get("stored_filename")
    content_type = payload.get("content_type", "video/mp4")
    size_bytes = payload.get("size_bytes")
    
    if not original_filename or not stored_filename:
        raise HTTPException(status_code=400, detail="original_filename and stored_filename are required")
        
    try:
        bucket = storage_client.bucket(GCS_VALIDATED_BUCKET)
        blob = bucket.blob(stored_filename)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Uploaded file not found in GCS validated bucket")
            
        # Set GCS metadata
        blob.metadata = {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "uploaded_via": "dashboard-api-signed-url",
        }
        blob.patch()
        blob.reload()
        
        # Write record to PostgreSQL video_uploads table
        await record_video_upload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size_bytes or blob.size,
            blob=blob,
        )
        
        logger.info("Direct GCS upload confirmed and registered in database: %s", original_filename)
        
        storage_status = build_storage_status(
            stored_filename,
            {
                "original_filename": original_filename,
                "content_type": content_type,
                "size_bytes": size_bytes or blob.size,
                "status": "stored",
            },
        )
        
        return {
            "status": "success",
            "original_filename": original_filename,
            "filename": stored_filename,
            "stored_filename": stored_filename,
            "bucket": GCS_VALIDATED_BUCKET,
            "gcs_uri": get_gcs_uri(GCS_VALIDATED_BUCKET, stored_filename),
            "execution_id": stored_filename,
            "storage": storage_status,
            "message": "Video stored and registered. Processing initiated."
        }
    except Exception as e:
        logger.exception("Failed to confirm upload: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to confirm upload: {str(e)}")


# ─── New Endpoint: Pipeline Status ──────────────────────────────────────────

@app.get("/api/v1/pipeline-status/{execution_id}")
async def get_pipeline_status(execution_id: str):
    """
    Check the status of a pipeline execution using either a Workflow Execution ID
    or a filename (e.g. sample.mp4).
    """
    try:
        upload_record = await get_video_upload_record(execution_id)
        storage_status = build_storage_status(execution_id, upload_record)
        pipeline_events = await get_pipeline_events(execution_id)

        # 1. Check if the file is in the quarantine bucket
        if storage_status["quarantine_exists"]:
            await update_video_upload_status(execution_id, "validation_failed")
            error_msg = "Validation failed: Video is corrupt or invalid."
            quarantine_bucket = storage_client.bucket(GCS_QUARANTINE_BUCKET)
            report_blob = quarantine_bucket.blob(f"{execution_id}.report.txt")
            if report_blob.exists():
                try:
                    raw_text = report_blob.download_as_text()
                    if isinstance(raw_text, bytes):
                        error_msg = raw_text.decode("utf-8").strip()
                    else:
                        error_msg = raw_text.strip()
                except Exception as report_error:
                    logger.warning(
                        "Could not read validation report for %s: %s",
                        execution_id,
                        report_error,
                    )
            return status_payload(
                execution_id=execution_id,
                state="FAILED",
                error=error_msg,
                storage={**storage_status, "status": "validation_failed"},
                events=pipeline_events,
            )

        client = executions_v1.ExecutionsClient()
        workflow_path = client.workflow_path(GCP_PROJECT, GCP_REGION, WORKFLOW_NAME)
        
        # 2. If it is a real execution ID (not a filename), query it directly
        is_filename = any(execution_id.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv'])
        
        if not is_filename:
            execution_path = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/workflows/{WORKFLOW_NAME}/executions/{execution_id}"
            execution = client.get_execution(name=execution_path)
            state = execution.state.name
            result = None
            error = None
            if execution.result:
                result = parse_optional_json(execution.result)
            if execution.error:
                error = str(execution.error)
            return status_payload(
                execution_id=execution_id,
                workflow_execution_id=execution_id,
                state=state,
                result=result,
                error=error,
                storage=storage_status,
                events=pipeline_events,
            )

        # 3. If it is a filename, search for recent workflow executions triggered for this file
        try:
            req = executions_v1.ListExecutionsRequest(
                parent=workflow_path,
                page_size=30
            )
            executions = client.list_executions(request=req)
            for exec_item in executions:
                if exec_item.argument and execution_id in exec_item.argument:
                    exec_id_found = exec_item.name.split("/")[-1]
                    state = exec_item.state.name
                    result = None
                    error = None
                    if exec_item.result:
                        result = parse_optional_json(exec_item.result)
                    if exec_item.error:
                        error = str(exec_item.error)
                    if state == "SUCCEEDED":
                        await update_video_upload_status(execution_id, "completed")
                        storage_status["status"] = "completed"
                    elif state == "FAILED":
                        await update_video_upload_status(execution_id, "pipeline_failed")
                        storage_status["status"] = "pipeline_failed"
                    return status_payload(
                        execution_id=execution_id,
                        workflow_execution_id=exec_id_found,
                        state=state,
                        result=result,
                        error=error,
                        storage=storage_status,
                        events=pipeline_events,
                    )
        except Exception as search_err:
            logger.warning(f"Error listing workflow executions: {search_err}")

        # 4. If inference results already landed in PostGIS, treat the pipeline as complete.
        # The validated GCS object is retained after processing, so GCS presence alone is not
        # a reliable signal that the workflow is still active.
        async with async_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM detections WHERE video_id = :video_id"),
                {"video_id": execution_id},
            )
            detections_saved = result.scalar() or 0

        if detections_saved:
            await update_video_upload_status(execution_id, "completed")
            storage_status["status"] = "completed"
            return status_payload(
                execution_id=execution_id,
                state="SUCCEEDED",
                result={
                    "status": "success",
                    "detections_saved": detections_saved,
                },
                storage=storage_status,
                events=pipeline_events,
            )

        latest_event = latest_pipeline_event(pipeline_events)
        if latest_event and str(latest_event.get("status")).upper() == "FAILED":
            await update_video_upload_status(execution_id, "pipeline_failed")
            storage_status["status"] = "pipeline_failed"
            return status_payload(
                execution_id=execution_id,
                state="FAILED",
                error=latest_event.get("message") or f"Pipeline failed at {latest_event.get('stage')}",
                storage=storage_status,
                events=pipeline_events,
            )

        timeout_reason = detect_pipeline_timeout(upload_record, pipeline_events)
        if timeout_reason:
            if not upload_record or upload_record.get("status") != "pipeline_timed_out":
                logger.error(
                    "PIPELINE_FAILURE stage=pipeline_timeout video_id=%s error=%s",
                    execution_id,
                    timeout_reason,
                )
                await update_video_upload_status(execution_id, "pipeline_timed_out")
            storage_status["status"] = "pipeline_timed_out"
            return status_payload(
                execution_id=execution_id,
                state="TIMED_OUT",
                result={"status": "timed_out"},
                error=timeout_reason,
                storage=storage_status,
                events=pipeline_events,
            )

        # 5. If no workflow is found but it's not quarantined, check if it's still being processed
        # Check raw bucket (validation in progress) or validated bucket (waiting for workflow to pick it up)
        if storage_status["raw_exists"] or storage_status["validated_exists"]:
            next_status = "validated" if storage_status["validated_exists"] else "stored"
            await update_video_upload_status(execution_id, next_status)
            storage_status["status"] = next_status
            return status_payload(
                execution_id=execution_id,
                state="ACTIVE",
                storage=storage_status,
                events=pipeline_events,
            )

        # Fallback if not found in GCS, DB, or workflows
        return status_payload(
            execution_id=execution_id,
            state="ACTIVE",
            storage=storage_status,
            events=pipeline_events,
        )

    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=status_check execution_id=%s error=%s", execution_id, e)
        raise HTTPException(status_code=500, detail=str(e))

# ─── Health Check ───────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
