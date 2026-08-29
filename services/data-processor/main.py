import os
import logging
import json
from typing import Any, Dict, Optional, List, Union
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing & Geocoding Service")

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
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

@app.on_event("startup")
async def ensure_pipeline_event_table():
    try:
        async with async_session() as session:
            await session.execute(text(PIPELINE_EVENTS_TABLE_SQL))
            await session.execute(text(PIPELINE_EVENTS_INDEX_SQL))
            await session.commit()
    except Exception as e:
        logger.exception("PIPELINE_FAILURE stage=data_processor_startup error=%s", e)
        raise

class DetectionItem(BaseModel):
    frame_id: str
    detection_type: str
    confidence: float
    model_name: Optional[str] = None
    model_family: Optional[str] = None
    model_group: Optional[str] = None
    category: Optional[str] = None
    label: Optional[str] = None
    method: Optional[str] = None
    annotation: Optional[Dict[str, Any]] = None

class BatchInferenceResult(BaseModel):
    video_id: str
    latitude: float
    longitude: float
    detections: List[DetectionItem]

class InferenceResult(BaseModel):
    video_id: str
    frame_id: str
    detection_type: str
    confidence: float
    latitude: float
    longitude: float
    annotation: Optional[Dict[str, Any]] = None

class PipelineEvent(BaseModel):
    video_id: str
    stage: str
    status: str
    execution_id: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@app.post("/pipeline-events")
async def record_pipeline_event(event: PipelineEvent):
    """
    Records a durable pipeline event for audit and status diagnostics.
    """
    logger.info(
        "PIPELINE_EVENT stage=%s status=%s video_id=%s",
        event.stage,
        event.status,
        event.video_id,
    )

    async with async_session() as session:
        try:
            await session.execute(
                text("""
                    INSERT INTO pipeline_events (
                        video_id,
                        execution_id,
                        stage,
                        status,
                        message,
                        details
                    )
                    VALUES (
                        :video_id,
                        :execution_id,
                        :stage,
                        :status,
                        :message,
                        CAST(:details AS JSONB)
                    )
                """),
                {
                    "video_id": event.video_id,
                    "execution_id": event.execution_id,
                    "stage": event.stage,
                    "status": event.status,
                    "message": event.message,
                    "details": json.dumps(event.details) if event.details else None,
                },
            )
            await session.commit()
            return {"status": "success"}
        except Exception as e:
            await session.rollback()
            logger.exception(
                "PIPELINE_FAILURE stage=pipeline_event_log video_id=%s event_stage=%s error=%s",
                event.video_id,
                event.stage,
                e,
            )
            raise HTTPException(status_code=500, detail="Pipeline event logging failed")

@app.post("/process")
async def process_inference(data: Union[BatchInferenceResult, InferenceResult]):
    """
    Receives inference results (either single or batch), formats as geospatial data,
    and writes them to PostGIS within a single transaction.
    """
    # Standardize input to a list of detections for batch insertion
    if isinstance(data, BatchInferenceResult):
        video_id = data.video_id
        latitude = data.latitude
        longitude = data.longitude
        detections = data.detections
    else:
        # Standardize legacy single InferenceResult into the batch format
        video_id = data.video_id
        latitude = data.latitude
        longitude = data.longitude
        detections = [
            DetectionItem(
                frame_id=data.frame_id,
                detection_type=data.detection_type,
                confidence=data.confidence,
                annotation=data.annotation
            )
        ]

    logger.info(f"Processing batch of {len(detections)} inference results for video: {video_id}")
    
    async with async_session() as session:
        try:
            # We insert all detections in a single database transaction block
            query = text("""
                INSERT INTO detections (video_id, frame_id, detection_type, confidence, location, timestamp, metadata)
                VALUES (
                    :video_id,
                    :frame_id,
                    :detection_type,
                    :confidence,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                    NOW(),
                    CAST(:metadata AS JSONB)
                )
            """)
            
            for det in detections:
                metadata = {
                    "annotation": det.annotation,
                    "model_name": det.model_name,
                    "model_family": det.model_family,
                    "model_group": det.model_group,
                    "category": det.category,
                    "label": det.label,
                    "method": det.method,
                }
                metadata = {key: value for key, value in metadata.items() if value is not None}
                await session.execute(query, {
                    "video_id": video_id,
                    "frame_id": det.frame_id,
                    "detection_type": det.detection_type,
                    "confidence": det.confidence,
                    "longitude": longitude,
                    "latitude": latitude,
                    "metadata": json.dumps(metadata) if metadata else None,
                })
            
            await session.commit()
            logger.info(f"Successfully recorded {len(detections)} detections for video: {video_id} in PostGIS")
            return {"status": "success", "message": f"{len(detections)} inference results recorded in PostGIS"}
        
        except Exception as e:
            await session.rollback()
            logger.exception(
                "PIPELINE_FAILURE stage=data_processor video_id=%s error=%s",
                video_id,
                e,
            )
            raise HTTPException(status_code=500, detail="Database write failed")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
