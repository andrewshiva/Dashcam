-- Cloud SQL (PostGIS) — Operational / Spatial Queries
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE highway_segments (
    id SERIAL PRIMARY KEY,
    nh_code VARCHAR(20) NOT NULL,
    segment_name VARCHAR(255),
    state VARCHAR(50),
    start_chainage NUMERIC(10,3),
    end_chainage NUMERIC(10,3),
    geom GEOMETRY(LINESTRING, 4326)
);

CREATE TABLE survey_runs (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(50),
    highway_segment_id INT REFERENCES highway_segments(id),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    raw_video_gcs_uri TEXT,
    status VARCHAR(20) DEFAULT 'uploaded'
);

CREATE TABLE video_uploads (
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
);

CREATE INDEX idx_video_uploads_stored_filename
    ON video_uploads (stored_filename);

CREATE TABLE pipeline_events (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    execution_id TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipeline_events_video_id_created_at
    ON pipeline_events (video_id, created_at DESC);

CREATE TABLE detections (
    id BIGSERIAL PRIMARY KEY,
    survey_run_id INT REFERENCES survey_runs(id),
    timestamp TIMESTAMPTZ,
    detection_type VARCHAR(50), -- pothole, crack, marking_fade, sign_damage
    severity VARCHAR(10),       -- low, medium, high, critical
    confidence NUMERIC(5,4),
    location GEOGRAPHY(POINT, 4326),
    video_id TEXT,
    chainage NUMERIC(10,3),
    frame_number INT,
    frame_id TEXT,
    frame_gcs_uri TEXT,
    metadata JSONB
);

CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    detection_id BIGINT REFERENCES detections(id),
    priority VARCHAR(10),
    status VARCHAR(20) DEFAULT 'open',
    assigned_to VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
