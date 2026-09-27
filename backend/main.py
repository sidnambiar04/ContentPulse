import json
from typing import Optional
from fastapi import FastAPI, Depends, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime

from database import get_db, engine, Base
from models import (
    Competitor,
    MonitoringSource,
    Article,
    MonitoringLog
)
from schemas import (
    CompetitorCreate,
    CompetitorUpdate,
    CompetitorResponse
)

from analyzer import analyze_website
from monitor import check_competitor as monitor_competitor
from scheduler import start_scheduler


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="ContentPulse API",
    description="Real-Time Competitor Content Monitoring Platform",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4444",
        "http://127.0.0.1:4444",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# START SCHEDULER & DATABASE TABLES
# ============================================================

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    start_scheduler()


# ============================================================
# BASIC ENDPOINTS
# ============================================================

@app.get("/")
def root():
    return {
        "message": "ContentPulse API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# CREATE COMPETITOR
# ============================================================

@app.post(
    "/competitors",
    response_model=CompetitorResponse
)
def create_competitor(
    competitor: CompetitorCreate,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # 1. Analyze the website
    # --------------------------------------------------------

    analysis = analyze_website(
        str(competitor.website_url)
    )

    # --------------------------------------------------------
    # 2. Create competitor record
    # --------------------------------------------------------

    new_competitor = Competitor(
        name=competitor.name,
        website_url=str(competitor.website_url),

        blog_url=analysis.get("blog_url"),
        rss_url=analysis.get("rss_url"),
        sitemap_url=analysis.get("sitemap_url"),

        monitoring_enabled=True,

        status=(
            "online"
            if analysis["success"]
            else "offline"
        )
    )

    db.add(new_competitor)
    db.commit()
    db.refresh(new_competitor)

    # --------------------------------------------------------
    # 3. Store discovered RSS source
    # --------------------------------------------------------

    if analysis.get("rss_url"):

        rss_source = MonitoringSource(
            competitor_id=new_competitor.id,
            source_type="rss",
            source_url=analysis["rss_url"],
            priority=1
        )

        db.add(rss_source)

    # --------------------------------------------------------
    # 4. Store discovered sitemap source
    # --------------------------------------------------------

    if analysis.get("sitemap_url"):

        sitemap_source = MonitoringSource(
            competitor_id=new_competitor.id,
            source_type="sitemap",
            source_url=analysis["sitemap_url"],
            priority=2
        )

        db.add(sitemap_source)

    # --------------------------------------------------------
    # 5. Store discovered direct blog/page source
    # --------------------------------------------------------

    if analysis.get("blog_url"):

        blog_source = MonitoringSource(
            competitor_id=new_competitor.id,
            source_type="direct_page",
            source_url=analysis["blog_url"],
            priority=3
        )

        db.add(blog_source)

    db.commit()

    return new_competitor


def safe_json_loads(val, default=None):
    if default is None:
        default = []
    if not val:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


# ============================================================
# GET ALL COMPETITORS
# ============================================================

@app.get(
    "/competitors",
    response_model=list[CompetitorResponse]
)
def get_competitors(
    db: Session = Depends(get_db)
):

    competitors = (
        db.query(Competitor)
        .order_by(Competitor.id.desc())
        .all()
    )

    # Count monitoring sources per competitor
    source_counts = dict(
        db.query(
            MonitoringSource.competitor_id,
            func.count(MonitoringSource.id)
        )
        .group_by(MonitoringSource.competitor_id)
        .all()
    )

    result = []
    for c in competitors:
        result.append({
            "id": c.id,
            "name": c.name,
            "website_url": c.website_url,
            "blog_url": c.blog_url,
            "rss_url": c.rss_url,
            "sitemap_url": c.sitemap_url,
            "monitoring_enabled": c.monitoring_enabled,
            "status": c.status,
            "last_checked": c.last_checked,
            "last_successful_detection": c.last_successful_detection,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "sources_count": source_counts.get(c.id, 0)
        })

    return result


# ============================================================
# GET SINGLE COMPETITOR DETAIL
# ============================================================

@app.get("/competitors/{competitor_id}")
def get_competitor_detail(
    competitor_id: int,
    db: Session = Depends(get_db)
):

    competitor = (
        db.query(Competitor)
        .filter(Competitor.id == competitor_id)
        .first()
    )

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    sources = (
        db.query(MonitoringSource)
        .filter(MonitoringSource.competitor_id == competitor_id)
        .all()
    )

    recent_articles = (
        db.query(Article)
        .filter(Article.competitor_id == competitor_id)
        .order_by(Article.detected_at.desc())
        .limit(10)
        .all()
    )

    recent_logs = (
        db.query(MonitoringLog)
        .filter(MonitoringLog.competitor_id == competitor_id)
        .order_by(MonitoringLog.checked_at.desc())
        .limit(10)
        .all()
    )

    articles_count = (
        db.query(func.count(Article.id))
        .filter(Article.competitor_id == competitor_id)
        .scalar()
    ) or 0

    return {
        "id": competitor.id,
        "name": competitor.name,
        "website_url": competitor.website_url,
        "blog_url": competitor.blog_url,
        "rss_url": competitor.rss_url,
        "sitemap_url": competitor.sitemap_url,
        "monitoring_enabled": competitor.monitoring_enabled,
        "status": competitor.status,
        "last_checked": competitor.last_checked,
        "last_successful_detection": competitor.last_successful_detection,
        "created_at": competitor.created_at,
        "updated_at": competitor.updated_at,
        "total_articles": articles_count,
        "sources": [
            {
                "id": s.id,
                "source_type": s.source_type,
                "source_url": s.source_url,
                "is_active": s.is_active,
                "priority": s.priority,
                "last_checked": s.last_checked,
                "last_success": s.last_success
            }
            for s in sources
        ],
        "recent_articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "detected_at": a.detected_at,
                "detection_delay_seconds": a.detection_delay_seconds,
                "detection_method": a.detection_method
            }
            for a in recent_articles
        ],
        "recent_logs": [
            {
                "id": l.id,
                "checked_at": l.checked_at,
                "success": l.success,
                "response_time_ms": l.response_time_ms,
                "articles_found": l.articles_found,
                "error_message": l.error_message
            }
            for l in recent_logs
        ]
    }


# ============================================================
# MANUALLY CHECK COMPETITOR
# ============================================================

@app.post("/competitors/{competitor_id}/check")
def check_competitor_endpoint(
    competitor_id: int,
    db: Session = Depends(get_db)
):

    competitor = (
        db.query(Competitor)
        .filter(
            Competitor.id == competitor_id
        )
        .first()
    )

    if not competitor:
        return {
            "success": False,
            "error": "Competitor not found"
        }

    result = monitor_competitor(
        competitor,
        db
    )

    return {
        "competitor": competitor.name,
        **result
    }


# ============================================================
# UPDATE COMPETITOR
# ============================================================

@app.patch("/competitors/{competitor_id}")
def update_competitor(
    competitor_id: int,
    data: Optional[CompetitorUpdate] = None,
    monitoring_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):

    competitor = (
        db.query(Competitor)
        .filter(
            Competitor.id == competitor_id
        )
        .first()
    )

    if not competitor:
        return {
            "success": False,
            "error": "Competitor not found"
        }

    if data:
        if data.name is not None:
            competitor.name = data.name.strip()
        if data.website_url is not None:
            competitor.website_url = str(data.website_url).strip()
        if data.blog_url is not None:
            competitor.blog_url = str(data.blog_url).strip() if data.blog_url else None
        if data.rss_url is not None:
            competitor.rss_url = str(data.rss_url).strip() if data.rss_url else None
        if data.sitemap_url is not None:
            competitor.sitemap_url = str(data.sitemap_url).strip() if data.sitemap_url else None
        if data.monitoring_enabled is not None:
            competitor.monitoring_enabled = data.monitoring_enabled

    if monitoring_enabled is not None:
        competitor.monitoring_enabled = monitoring_enabled

    competitor.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(competitor)

    return {
        "success": True,
        "id": competitor.id,
        "name": competitor.name,
        "website_url": competitor.website_url,
        "blog_url": competitor.blog_url,
        "rss_url": competitor.rss_url,
        "sitemap_url": competitor.sitemap_url,
        "monitoring_enabled": competitor.monitoring_enabled,
        "status": competitor.status
    }


# ============================================================
# DELETE COMPETITOR
# ============================================================

@app.delete("/competitors/{competitor_id}")
def delete_competitor(
    competitor_id: int,
    db: Session = Depends(get_db)
):

    competitor = (
        db.query(Competitor)
        .filter(
            Competitor.id == competitor_id
        )
        .first()
    )

    if not competitor:
        return {
            "success": False,
            "error": "Competitor not found"
        }

    # Clean up associated records safely
    db.query(Article).filter(Article.competitor_id == competitor_id).delete(synchronize_session=False)
    db.query(MonitoringSource).filter(MonitoringSource.competitor_id == competitor_id).delete(synchronize_session=False)
    db.query(MonitoringLog).filter(MonitoringLog.competitor_id == competitor_id).delete(synchronize_session=False)

    db.delete(competitor)
    db.commit()

    return {
        "success": True,
        "message": "Competitor deleted successfully"
    }


# ============================================================
# GET ALL ARTICLES (WITH FILTERS & SEARCH)
# ============================================================

@app.get("/articles")
def get_articles(
    competitor_id: Optional[int] = None,
    detection_method: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):

    query = (
        db.query(Article, Competitor.name.label("competitor_name"))
        .outerjoin(Competitor, Article.competitor_id == Competitor.id)
    )

    if competitor_id:
        query = query.filter(Article.competitor_id == competitor_id)

    if detection_method and detection_method.lower() != "all":
        query = query.filter(func.lower(Article.detection_method) == detection_method.lower())

    if status and status.lower() != "all":
        query = query.filter(func.lower(Article.status) == status.lower())

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Article.title.ilike(search_pattern),
                Article.author.ilike(search_pattern),
                Article.url.ilike(search_pattern),
                Article.meta_description.ilike(search_pattern)
            )
        )

    articles = (
        query.order_by(
            Article.detected_at.desc()
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": article.id,
            "competitor_id": article.competitor_id,
            "competitor_name": comp_name or f"Competitor #{article.competitor_id}",
            "title": article.title,
            "url": article.url,
            "canonical_url": article.canonical_url,
            "author": article.author,
            "published_at": article.published_at,
            "detected_at": article.detected_at,
            "detection_delay_seconds": article.detection_delay_seconds,
            "detection_method": article.detection_method,
            "check_id": article.check_id,
            "featured_image_url": article.featured_image_url,
            "meta_description": article.meta_description,
            "categories": safe_json_loads(article.categories, []),
            "tags": safe_json_loads(article.tags, []),
            "relevant_links": safe_json_loads(article.relevant_links, []),
            "content_preview": (
                article.content[:240] + "..."
                if article.content and len(article.content) > 240
                else article.content
            ),
            "status": article.status
        }
        for article, comp_name in articles
    ]


# ============================================================
# GET SINGLE ARTICLE
# ============================================================

@app.get("/articles/{article_id}")
def get_article(
    article_id: int,
    db: Session = Depends(get_db)
):

    result = (
        db.query(Article, Competitor.name.label("competitor_name"))
        .outerjoin(Competitor, Article.competitor_id == Competitor.id)
        .filter(Article.id == article_id)
        .first()
    )

    if not result:
        return {
            "success": False,
            "error": "Article not found"
        }

    article, comp_name = result

    return {
        "id": article.id,
        "competitor_id": article.competitor_id,
        "competitor_name": comp_name or f"Competitor #{article.competitor_id}",
        "title": article.title,
        "url": article.url,
        "canonical_url": article.canonical_url,
        "content": article.content,
        "author": article.author,
        "published_at": article.published_at,
        "detected_at": article.detected_at,
        "detection_delay_seconds": (
            article.detection_delay_seconds
        ),
        "detection_method": (
            article.detection_method
        ),
        "check_id": article.check_id,
        "featured_image_url": (
            article.featured_image_url
        ),
        "meta_description": (
            article.meta_description
        ),
        "categories": safe_json_loads(article.categories, []),
        "tags": safe_json_loads(article.tags, []),
        "relevant_links": safe_json_loads(article.relevant_links, []),
        "status": article.status
    }


# ============================================================
# GET MONITORING LOGS
# ============================================================

@app.get("/monitoring/logs")
def get_monitoring_logs(
    competitor_id: Optional[int] = None,
    success: Optional[bool] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):

    query = (
        db.query(MonitoringLog, Competitor.name.label("competitor_name"))
        .outerjoin(Competitor, MonitoringLog.competitor_id == Competitor.id)
    )

    if competitor_id:
        query = query.filter(MonitoringLog.competitor_id == competitor_id)

    if success is not None:
        query = query.filter(MonitoringLog.success == success)

    logs = (
        query.order_by(
            MonitoringLog.checked_at.desc()
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "competitor_id": log.competitor_id,
            "competitor_name": comp_name or f"Competitor #{log.competitor_id}",
            "source_id": log.source_id,
            "checked_at": log.checked_at,
            "success": log.success,
            "response_time_ms": (
                log.response_time_ms
            ),
            "articles_found": (
                log.articles_found
            ),
            "error_message": (
                log.error_message
            )
        }
        for log, comp_name in logs
    ]


# ============================================================
# DASHBOARD & PERFORMANCE STATISTICS
# ============================================================

@app.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db)
):

    competitors = (
        db.query(Competitor)
        .all()
    )

    articles = (
        db.query(Article)
        .all()
    )

    logs = (
        db.query(MonitoringLog)
        .all()
    )

    # --------------------------------------------------------
    # Competitor statistics
    # --------------------------------------------------------

    enabled_competitors = sum(
        1
        for c in competitors
        if c.monitoring_enabled
    )

    online_competitors = sum(
        1
        for c in competitors
        if c.status == "online"
    )

    offline_competitors = sum(
        1
        for c in competitors
        if c.status == "offline"
    )

    no_source_competitors = sum(
        1
        for c in competitors
        if not c.rss_url and not c.sitemap_url and not c.blog_url
    )

    # --------------------------------------------------------
    # Monitoring statistics
    # --------------------------------------------------------

    total_checks = len(logs)
    successful_checks = sum(
        1
        for log in logs
        if log.success
    )

    failed_checks = total_checks - successful_checks

    success_rate_percent = (
        round((successful_checks / total_checks) * 100, 1)
        if total_checks > 0
        else 100.0
    )

    # Response time metrics
    response_times = [
        log.response_time_ms
        for log in logs
        if log.response_time_ms is not None and log.response_time_ms > 0
    ]

    avg_response_time_ms = (
        round(sum(response_times) / len(response_times), 1)
        if response_times
        else 0
    )

    fastest_response_ms = min(response_times) if response_times else 0
    slowest_response_ms = max(response_times) if response_times else 0

    # --------------------------------------------------------
    # Detection delay statistics
    # --------------------------------------------------------

    delays = [
        article.detection_delay_seconds
        for article in articles
        if article.detection_delay_seconds is not None and article.detection_delay_seconds >= 0
    ]

    average_delay = (
        sum(delays) / len(delays)
        if delays
        else 0
    )

    fastest_delay = (
        min(delays)
        if delays
        else 0
    )

    slowest_delay = (
        max(delays)
        if delays
        else 0
    )

    # --------------------------------------------------------
    # Breakdown: Articles by Competitor
    # --------------------------------------------------------

    comp_name_map = {c.id: c.name for c in competitors}
    article_counts_by_comp = {}
    for a in articles:
        article_counts_by_comp[a.competitor_id] = (
            article_counts_by_comp.get(a.competitor_id, 0) + 1
        )

    articles_by_competitor = [
        {
            "competitor_id": comp_id,
            "competitor_name": comp_name_map.get(comp_id, f"Competitor #{comp_id}"),
            "count": count
        }
        for comp_id, count in sorted(
            article_counts_by_comp.items(),
            key=lambda item: item[1],
            reverse=True
        )[:8]
    ]

    # --------------------------------------------------------
    # Breakdown: Detection Methods Distribution
    # --------------------------------------------------------

    method_counts = {}
    for a in articles:
        method = (a.detection_method or "unknown").lower()
        method_counts[method] = method_counts.get(method, 0) + 1

    # --------------------------------------------------------
    # Breakdown: Delay ranges
    # --------------------------------------------------------

    delay_ranges = {
        "under_30s": sum(1 for d in delays if d < 30),
        "30s_to_2m": sum(1 for d in delays if 30 <= d < 120),
        "2m_to_10m": sum(1 for d in delays if 120 <= d < 600),
        "over_10m": sum(1 for d in delays if d >= 600),
    }

    # --------------------------------------------------------
    # Return complete dashboard data
    # --------------------------------------------------------

    return {
        "total_competitors": len(competitors),
        "enabled_competitors": enabled_competitors,
        "online_competitors": online_competitors,
        "offline_competitors": offline_competitors,
        "no_source_competitors": no_source_competitors,
        "total_articles": len(articles),
        "total_checks": total_checks,
        "successful_checks": successful_checks,
        "failed_checks": failed_checks,
        "success_rate_percent": success_rate_percent,
        "average_detection_delay_seconds": round(average_delay, 2),
        "fastest_detection_delay_seconds": fastest_delay,
        "slowest_detection_delay_seconds": slowest_delay,
        "average_response_time_ms": avg_response_time_ms,
        "fastest_response_time_ms": fastest_response_ms,
        "slowest_response_time_ms": slowest_response_ms,
        "articles_by_competitor": articles_by_competitor,
        "detection_methods": method_counts,
        "delay_ranges": delay_ranges
    }