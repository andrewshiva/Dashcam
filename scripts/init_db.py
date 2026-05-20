import sqlalchemy
from sqlalchemy import text
import time

import os

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "nhaidb")

def main():
    engine = sqlalchemy.create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
    
    with engine.connect() as conn:
        print("Enabling PostGIS extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
        
        print("Creating detections table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS detections (
                id SERIAL PRIMARY KEY,
                video_id TEXT NOT NULL,
                frame_id TEXT,
                detection_type TEXT NOT NULL,
                confidence FLOAT NOT NULL,
                location GEOMETRY(Point, 4326),
                chainage NUMERIC(10,3),
                frame_gcs_uri TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """))
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS frame_id TEXT;"))
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS chainage NUMERIC(10,3);"))
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS frame_gcs_uri TEXT;"))
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS metadata JSONB;"))

        print("Creating video_uploads table...")
        conn.execute(text("""
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
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_video_uploads_stored_filename
            ON video_uploads (stored_filename);
        """))

        print("Creating pipeline_events table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_events (
                id BIGSERIAL PRIMARY KEY,
                video_id TEXT NOT NULL,
                execution_id TEXT,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                details JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pipeline_events_video_id_created_at
            ON pipeline_events (video_id, created_at DESC);
        """))
        conn.commit()
        
        print("Database initialization complete!")

if __name__ == "__main__":
    main()
