from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey
)
from datetime import datetime

from database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    website_url = Column(Text, nullable=False)
    blog_url = Column(Text)
    rss_url = Column(Text)
    sitemap_url = Column(Text)

    monitoring_enabled = Column(Boolean, default=True)
    status = Column(String(50), default="unknown")

    last_checked = Column(DateTime)
    last_successful_detection = Column(DateTime)

    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class MonitoringSource(Base):
    __tablename__ = "monitoring_sources"

    id = Column(Integer, primary_key=True)

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False
    )

    source_type = Column(String(50), nullable=False)
    source_url = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)

    last_checked = Column(DateTime)
    last_success = Column(Boolean)

    created_at = Column(DateTime)

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False
    )

    title = Column(Text, nullable=False)
    url = Column(Text)
    canonical_url = Column(Text)
    content = Column(Text)
    author = Column(String(255))
    published_at = Column(DateTime)
    detected_at = Column(DateTime, nullable=False)
    detection_delay_seconds = Column(Integer)
    detection_method = Column(String(50))
    check_id = Column(String(100))
    featured_image_url = Column(Text)
    meta_description = Column(Text)
    categories = Column(Text)
    tags = Column(Text)

    # ADD THIS
    relevant_links = Column(Text)

    status = Column(
        String(50),
        default="new"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    id = Column(Integer, primary_key=True)

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False
    )

    source_id = Column(
        Integer,
        ForeignKey("monitoring_sources.id")
    )

    checked_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    success = Column(
        Boolean,
        default=False
    )

    response_time_ms = Column(Integer)

    articles_found = Column(
        Integer,
        default=0
    )

    error_message = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )