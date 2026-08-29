import sqlalchemy
from sqlalchemy import text

import os

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "nhaidb")

def main():
    if not DB_PASS:
        raise RuntimeError("Set DB_PASSWORD or DB_PASS before running database migration.")

    engine = sqlalchemy.create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
    with engine.connect() as conn:
        print("Altering detections table to add frame_id...")
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS frame_id TEXT;"))
        print("Altering detections table to add chainage...")
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS chainage NUMERIC(10,3);"))
        print("Altering detections table to add frame_gcs_uri...")
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS frame_gcs_uri TEXT;"))
        print("Altering detections table to add metadata...")
        conn.execute(text("ALTER TABLE detections ADD COLUMN IF NOT EXISTS metadata JSONB;"))
        conn.commit()
        print("Success!")

if __name__ == "__main__":
    main()
