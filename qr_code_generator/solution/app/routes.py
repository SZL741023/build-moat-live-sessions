from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
import io
import qrcode
import logging
from sqlalchemy.orm import Session
from .database import get_db
from .models import UrlMapping, ScanEvent
from .schema import (
    CreateRequest,
    CreateResponse,
    QrInfoResponse,
    ScanByDay,
    UpdateRequest,
    AnalyticsResponse,
)
from .token_gen import generate_token
from .url_validate import validate_url

router = APIRouter()

redirect_cache: dict[str, str] = {}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_URL = "http://localhost:8000"


@router.post("/api/qr/create", response_model=CreateResponse)
def create_qr(req: CreateRequest, db: Session = Depends(get_db)):
    normalize_url = validate_url(req.url)
    token = generate_token(normalize_url)

    redirect_cache[token] = normalize_url

    mapping = UrlMapping(token=token, original_url=normalize_url)
    db.add(mapping)
    db.commit()

    return CreateResponse(
        token=token,
        short_url=f"{BASE_URL}/r/{token}",
        qr_code_url=f"{BASE_URL}/api/qr/{token}/image",
        original_url=normalize_url,
    )


@router.get("/r/{token}")
def redirect(token: str, req: Request, db: Session = Depends(get_db)):

    if token in redirect_cache:
        logger.info(f"[CACHE HIT] token={token}")
        _record_scan(token, req, db)
        return RedirectResponse(url=redirect_cache[token], status_code=302)

    mapping = _get_mapping_or_404(token, db)

    if mapping.is_deleted:
        raise HTTPException(status_code=410)

    utc_now = datetime.now(timezone.utc)

    if mapping.expires_at and mapping.expires_at < utc_now:
        raise HTTPException(status_code=410)

    logger.info(f"[DB HIT] token={token}")
    redirect_cache[token] = mapping.original_url
    _record_scan(token, req, db)
    return RedirectResponse(url=mapping.original_url, status_code=302)


@router.get("/api/qr/{token}", response_model=QrInfoResponse)
def get_qr_info(token: str, db: Session = Depends(get_db)):
    mapping = _get_mapping_or_404(token, db)

    return QrInfoResponse(
        token=mapping.token,
        original_url=mapping.original_url,
        create_at=mapping.create_at,
        updated_at=mapping.updated_at,
        expires_at=mapping.expires_at,
        is_deleted=mapping.is_deleted,
    )


@router.patch("/api/qr/{token}", response_model=QrInfoResponse)
def update_qr(token: str, req: UpdateRequest, db: Session = Depends(get_db)):
    mapping = db.query(UrlMapping).filter(UrlMapping.token == token).first()

    if not mapping:
        raise HTTPException(status_code=404)

    if req.url:
        mapping.original_url = req.url

    if req.expires_at:
        mapping.expires_at = req.expires_at

    db.commit()
    return QrInfoResponse(
        token=mapping.token,
        original_url=mapping.original_url,
        create_at=mapping.create_at,
        updated_at=mapping.updated_at,
        expires_at=mapping.expires_at,
        is_deleted=mapping.is_deleted,
    )


@router.delete("/api/qr/{token}")
def delete_qr(token: str, db: Session = Depends(get_db)):
    mapping = _get_mapping_or_404(token, db)

    mapping.is_deleted = True
    redirect_cache.pop(token, None)
    db.commit()
    return {"message": "deleted sucussfully"}


@router.get("/api/qr/{token}/image")
def get_qr_img(token: str, db: Session = Depends(get_db)):
    _get_mapping_or_404(token, db)

    short_url = f"{BASE_URL}/r/{token}"
    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/api/qr/{token}/analytics", response_model=AnalyticsResponse)
def get_qr_analytics(token: str, db: Session = Depends(get_db)):
    _get_mapping_or_404(token, db)

    events = db.query(ScanEvent).filter(ScanEvent.token == token).all()

    counts = {}

    for event in events:
        day = event.scanned_at.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    scans_by_day = [ScanByDay(date=day, count=count) for day, count in counts.items()]

    return AnalyticsResponse(
        token=token, total_scans=len(events), scans_by_day=scans_by_day
    )


def _get_mapping_or_404(token: str, db: Session) -> UrlMapping:
    mapping = db.query(UrlMapping).filter(UrlMapping.token == token).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Not found")

    return mapping


def _record_scan(token: str, req: Request, db: Session = Depends(get_db)):
    event = ScanEvent(
        token=token,
        user_agent=req.headers.get("user-agent"),
        ip_address=req.client.host if req.client else None,
    )
    db.add(event)
    db.commit()
