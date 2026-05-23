import io
import json
import logging
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import quote_plus
from xml.sax.saxutils import escape

from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse
from google.cloud import storage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NHAI DAS Spatial Reporting Service")

@app.middleware("http")
async def log_unhandled_pipeline_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(
            "PIPELINE_FAILURE stage=report_generator path=%s error=%s",
            request.url.path,
            exc,
        )
        raise

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

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "nhai-das-dev-processed")
_storage_client = None


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def env_default(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback)


def parse_metadata(raw_metadata: Any) -> Dict[str, Any]:
    if isinstance(raw_metadata, dict):
        return raw_metadata
    if isinstance(raw_metadata, str):
        try:
            parsed = json.loads(raw_metadata)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    if value:
        return str(value).split(" ")[0]
    return ""


def format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    if value:
        raw_value = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            return parsed.strftime("%d-%m-%Y %H:%M")
        except ValueError:
            return raw_value.replace("T", " ")
    return ""


def format_decimal(value: Any, places: int = 6) -> str:
    if value is None:
        return ""
    number = float(value) if isinstance(value, Decimal) else value
    try:
        return f"{float(number):.{places}f}"
    except (TypeError, ValueError):
        return str(value)


def format_chainage(value: Any, latitude: Any, longitude: Any) -> str:
    if value not in (None, ""):
        try:
            return f"KM {float(value):.3f}"
        except (TypeError, ValueError):
            return str(value)

    if latitude is None or longitude is None:
        return ""

    lat_component = int(abs(float(latitude)) * 10)
    lng_component = int((abs(float(longitude)) * 1000) % 1000)
    return f"KM {lat_component}+{lng_component:03d}"


def defect_label(value: str) -> str:
    return (value or "Unknown").replace("_", " ").title()


def image_blob_path(video_id: str, row: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[str]:
    if row.get("frame_gcs_uri"):
        uri = row["frame_gcs_uri"]
        if uri.startswith("gs://"):
            parts = uri.replace("gs://", "", 1).split("/", 1)
            return parts[1] if len(parts) == 2 and parts[0] == PROCESSED_BUCKET else None
        return uri

    frame_uri = metadata.get("frame_gcs_uri") or metadata.get("image_gcs_uri")
    if isinstance(frame_uri, str) and frame_uri.startswith("gs://"):
        parts = frame_uri.replace("gs://", "", 1).split("/", 1)
        return parts[1] if len(parts) == 2 and parts[0] == PROCESSED_BUCKET else None

    frame_id = row.get("frame_id") or metadata.get("frame_id") or "frame_0000.jpg"
    base_name = os.path.splitext(video_id)[0]
    return f"frames/{base_name}/{frame_id}"


def download_defect_image(video_id: str, row: Dict[str, Any], temp_dir: str) -> Optional[str]:
    metadata = parse_metadata(row.get("metadata"))
    blob_path = image_blob_path(video_id, row, metadata)
    if not blob_path:
        return None

    try:
        bucket = get_storage_client().bucket(PROCESSED_BUCKET)
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return None

        local_path = os.path.join(temp_dir, f"defect_{row['id']}.jpg")
        blob.download_to_filename(local_path)
        return local_path
    except Exception as exc:
        logger.warning("Could not load defect image %s: %s", blob_path, exc)
        return None


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=styles["Normal"],
            alignment=1,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceAfter=16,
        ),
        "appendix": ParagraphStyle(
            "Appendix",
            parent=styles["Normal"],
            alignment=2,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Normal"],
            alignment=1,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceAfter=14,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            spaceAfter=8,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontSize=7,
            leading=8,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=1,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=styles["Italic"],
            fontSize=7,
            leading=9,
            spaceBefore=8,
        ),
    }


def table_style(header_background=colors.HexColor("#f3f4f6")):
    return TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), header_background),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )





def build_project_details_table(project_details: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> Table:
    rows = [[
        Paragraph("S. No.", styles["cell_bold"]),
        Paragraph("Description", styles["cell_bold"]),
        Paragraph("Details", styles["cell_bold"]),
    ]]

    descriptions = [
        ("NH Number", "nh_number"),
        ("Name of the Project", "project_name"),
        ("UPC Code", "upc_code"),
        ("Start Chainage", "start_chainage"),
        ("End Chainage", "end_chainage"),
        ("Project Length", "project_length"),
        ("Name of the State", "state_name"),
        ("RO Name", "ro_name"),
        ("PIU Name", "piu_name"),
        ("Survey Date & Time", "survey_date"),
    ]

    for index, (label, key) in enumerate(descriptions, start=1):
        rows.append([
            Paragraph(str(index), styles["cell"]),
            Paragraph(label, styles["cell"]),
            Paragraph(project_details.get(key) or "", styles["cell"]),
        ])

    table = Table(rows, colWidths=[45, 220, 270], repeatRows=1)
    table.setStyle(table_style())
    return table


def compact_video_name(video_id: str, max_length: int = 36) -> str:
    text = str(video_id or "Unknown video")
    if len(text) <= max_length:
        return text
    side = max(4, (max_length - 3) // 2)
    return f"{text[:side]}...{text[-side:]}"


def image_cell(path: Optional[str], styles: Dict[str, ParagraphStyle], video_id: str):
    source_caption = Paragraph(f"Video:<br/>{escape(compact_video_name(video_id))}", styles["cell"])
    if not path:
        return [Paragraph("Not available", styles["cell"]), Spacer(1, 2), source_caption]
    try:
        return [Image(path, width=58, height=38), Spacer(1, 2), source_caption]
    except Exception as exc:
        logger.warning("Could not render report image %s: %s", path, exc)
        return [Paragraph("Not available", styles["cell"]), Spacer(1, 2), source_caption]


def build_defect_output_table(
    video_id: str,
    defects,
    temp_dir: str,
    styles: Dict[str, ParagraphStyle],
) -> Table:
    rows = [[
        Paragraph("S.<br/>No.", styles["cell_bold"]),
        Paragraph("Reporting<br/>Date", styles["cell_bold"]),
        Paragraph("Asset<br/>Type", styles["cell_bold"]),
        Paragraph("Defect<br/>Description", styles["cell_bold"]),
        Paragraph("Side", styles["cell_bold"]),
        Paragraph("Chainage", styles["cell_bold"]),
        Paragraph("Latitude", styles["cell_bold"]),
        Paragraph("Longitude", styles["cell_bold"]),
        Paragraph("Defect<br/>Image", styles["cell_bold"]),
    ]]

    if not defects:
        rows.append([
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("No defects recorded for this video.", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
        ])

    for index, row in enumerate(defects, start=1):
        metadata = parse_metadata(row.get("metadata"))
        side = metadata.get("side") or row.get("side") or "Carriageway"
        asset_type = metadata.get("asset_type") or metadata.get("category") or row.get("asset_type") or "Road Surface"
        chainage = format_chainage(row.get("chainage"), row.get("lat"), row.get("lng"))
        local_image_path = download_defect_image(video_id, row, temp_dir)

        rows.append([
            Paragraph(str(index), styles["cell"]),
            Paragraph(format_date(row.get("timestamp")), styles["cell"]),
            Paragraph(defect_label(asset_type), styles["cell"]),
            Paragraph(metadata.get("label") or defect_label(row.get("detection_type")), styles["cell"]),
            Paragraph(side, styles["cell"]),
            Paragraph(chainage, styles["cell"]),
            Paragraph(format_decimal(row.get("lat")), styles["cell"]),
            Paragraph(format_decimal(row.get("lng")), styles["cell"]),
            image_cell(local_image_path, styles, video_id),
        ])

    table = Table(
        rows,
        colWidths=[28, 54, 64, 90, 45, 60, 55, 55, 84],
        repeatRows=1,
    )
    table.setStyle(table_style())
    return table


@app.get("/generate-report/{video_id}")
async def generate_report(
    video_id: str,
    nh_number: Optional[str] = Query(default=None),
    project_name: Optional[str] = Query(default=None),
    upc_code: Optional[str] = Query(default=None),
    start_chainage: Optional[str] = Query(default=None),
    end_chainage: Optional[str] = Query(default=None),
    project_length: Optional[str] = Query(default=None),
    state_name: Optional[str] = Query(default=None),
    ro_name: Optional[str] = Query(default=None),
    piu_name: Optional[str] = Query(default=None),
    survey_date: Optional[str] = Query(default=None),
):
    """
    Generates an NHAI road condition survey report for a video run.
    """


    async with async_session() as session:
        query = text(
            """
            SELECT id, detection_type, confidence,
                   ST_Y(location::geometry) as lat,
                   ST_X(location::geometry) as lng,
                   timestamp, frame_id, chainage, frame_gcs_uri, metadata
            FROM detections
            WHERE video_id = :video_id
              AND detection_type != 'road_clear'
            ORDER BY timestamp ASC
            """
        )
        result = await session.execute(query, {"video_id": video_id})
        defects = [dict(row) for row in result.mappings().all()]

    first_timestamp = defects[0]["timestamp"] if defects else datetime.utcnow()
    project_details = {
        "nh_number": nh_number or env_default("REPORT_NH_NUMBER", "NH-44"),
        "project_name": project_name or env_default("REPORT_PROJECT_NAME", "Dashcam Analytics Road Condition Survey"),
        "upc_code": upc_code or env_default("REPORT_UPC_CODE", ""),
        "start_chainage": start_chainage or env_default("REPORT_START_CHAINAGE", ""),
        "end_chainage": end_chainage or env_default("REPORT_END_CHAINAGE", ""),
        "project_length": project_length or env_default("REPORT_PROJECT_LENGTH", ""),
        "state_name": state_name or env_default("REPORT_STATE_NAME", ""),
        "ro_name": ro_name or env_default("REPORT_RO_NAME", ""),
        "piu_name": piu_name or env_default("REPORT_PIU_NAME", ""),
        "survey_date": format_datetime(survey_date or env_default("REPORT_SURVEY_DATE", "") or first_timestamp),
    }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=34,
        bottomMargin=34,
    )
    styles = make_styles()

    elements = [
        Paragraph("<u>NATIONAL HIGHWAYS AUTHORITY OF INDIA</u>", styles["title"]),
        Paragraph("ROAD CONDITION SURVEY REPORT", styles["section"]),
        Paragraph(
            "The following table lists the project fields to be populated for the surveyed highway section.",
            styles["body"],
        ),
        build_project_details_table(project_details, styles),
        Spacer(1, 12),
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        elements.append(build_defect_output_table(video_id, defects, temp_dir, styles))
        doc.build(elements)

    buffer.seek(0)
    base_name = os.path.splitext(video_id)[0]
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=road_condition_survey_report_{base_name}.pdf"},
    )


@app.get("/health")
def health_check():
    return {"status": "healthy"}
