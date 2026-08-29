import json
import mimetypes
import os
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = os.environ.get(
    "DASHBOARD_API_BASE",
    "https://dashboard-api-863438916962.asia-south1.run.app",
).rstrip("/")
SAMPLE_VIDEO = Path(os.environ.get("SAMPLE_VIDEO", "Sample/1_N0200112004GJ.mp4"))
POLL_TIMEOUT_SECONDS = int(os.environ.get("PIPELINE_POLL_TIMEOUT_SECONDS", "600"))
POLL_INTERVAL_SECONDS = int(os.environ.get("PIPELINE_POLL_INTERVAL_SECONDS", "10"))


def request_json(url, method="GET", body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc


def upload_video(path):
    content_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    file_bytes = path.read_bytes()

    # 1. Generate GCS Signed URL
    print(f"Generating secure signed upload URL for {path.name}...")
    url_payload = json.dumps({
        "filename": path.name,
        "content_type": content_type
    }).encode("utf-8")

    url_response = request_json(
        f"{API_BASE}/api/v1/generate-upload-url",
        method="POST",
        body=url_payload,
        headers={"Content-Type": "application/json"}
    )

    upload_url = url_response.get("upload_url")
    stored_filename = url_response.get("stored_filename")
    if not upload_url or not stored_filename:
        raise RuntimeError(f"Failed to get upload_url or stored_filename from API: {url_response}")

    # 2. Upload raw file binary to GCS via PUT
    print(f"Uploading raw bytes ({len(file_bytes)} bytes) directly to GCS via Signed URL...")
    req = urllib.request.Request(
        upload_url,
        data=file_bytes,
        method="PUT",
        headers={"Content-Type": content_type}
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GCS Signed URL PUT failed: {exc.code} {detail}") from exc

    # 3. Confirm upload with dashboard-api
    print("Confirming and registering upload with backend...")
    confirm_payload = json.dumps({
        "original_filename": path.name,
        "stored_filename": stored_filename,
        "content_type": content_type,
        "size_bytes": len(file_bytes)
    }).encode("utf-8")

    return request_json(
        f"{API_BASE}/api/v1/confirm-upload",
        method="POST",
        body=confirm_payload,
        headers={"Content-Type": "application/json"}
    )


def assert_storage_record(status_payload):
    storage = status_payload.get("storage") or {}
    stored_filename = storage.get("stored_filename")
    if not stored_filename:
        raise AssertionError("Status response did not include stored_filename.")

    exists_somewhere = any(
        storage.get(key)
        for key in ("raw_exists", "validated_exists", "quarantine_exists")
    )
    if not exists_somewhere:
        raise AssertionError(
            f"{stored_filename} is not visible in raw, validated, or quarantine storage."
        )


def main():
    if not SAMPLE_VIDEO.exists():
        raise FileNotFoundError(f"Sample video not found: {SAMPLE_VIDEO}")

    print(f"Uploading {SAMPLE_VIDEO} directly to GCS...")
    upload_response = upload_video(SAMPLE_VIDEO)
    print(json.dumps(upload_response, indent=2))

    execution_id = upload_response.get("execution_id")
    if not execution_id:
        raise AssertionError("Upload response did not include execution_id.")

    deadline = time.time() + POLL_TIMEOUT_SECONDS
    last_status = None

    while time.time() < deadline:
        last_status = request_json(f"{API_BASE}/api/v1/pipeline-status/{execution_id}")
        assert_storage_record(last_status)
        print(json.dumps({
            "state": last_status.get("state"),
            "execution_id": last_status.get("execution_id"),
            "storage": last_status.get("storage"),
        }, indent=2))

        if last_status.get("state") == "SUCCEEDED":
            print("Pipeline verified: video stored and processing completed.")
            return 0

        if last_status.get("state") == "FAILED":
            raise RuntimeError(f"Pipeline failed: {last_status.get('error')}")

        time.sleep(POLL_INTERVAL_SECONDS)

    print("Video storage verified, but processing did not complete before timeout.")
    print(json.dumps(last_status, indent=2))
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
