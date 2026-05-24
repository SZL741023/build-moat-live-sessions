from pydantic import BaseModel
from datetime import datetime


class CreateRequest(BaseModel):
    url: str


class CreateResponse(BaseModel):
    token: str
    short_url: str
    qr_code_url: str
    original_url: str


class UpdateRequest(BaseModel):
    url: str | None = None
    expires_at: datetime | None = None


class QrInfoResponse(BaseModel):
    token: str
    original_url: str
    create_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    is_deleted: bool


class ScanByDay(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    token: str
    total_scans: int
    scans_by_day: list[ScanByDay]
