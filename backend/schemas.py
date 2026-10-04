from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any
from datetime import datetime


class CompetitorCreate(BaseModel):
    name: str
    website_url: str
    blog_url: Optional[str] = None
    check_interval_minutes: Optional[int] = 1


class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    blog_url: Optional[str] = None
    rss_url: Optional[str] = None
    sitemap_url: Optional[str] = None
    monitoring_enabled: Optional[bool] = None
    check_interval_minutes: Optional[int] = None


class MonitoringSourceResponse(BaseModel):
    id: int
    competitor_id: int
    source_type: str
    source_url: str
    is_active: bool
    priority: int
    last_checked: Optional[datetime] = None
    last_success: Optional[bool] = None

    class Config:
        from_attributes = True


class CompetitorResponse(BaseModel):
    id: int
    name: str
    website_url: str
    blog_url: Optional[str] = None
    rss_url: Optional[str] = None
    sitemap_url: Optional[str] = None

    monitoring_enabled: bool
    status: str
    check_interval_minutes: Optional[int] = 1

    last_checked: Optional[datetime] = None
    last_successful_detection: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sources_count: Optional[int] = 0

    class Config:
        from_attributes = True