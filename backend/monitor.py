import json
import time
import uuid
import feedparser
import requests

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from urllib.parse import urljoin, urlparse
from http_utils import request_with_retry

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from models import (
    Competitor,
    Article,
    MonitoringLog,
    MonitoringSource
)

from article_parser import parse_article

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

RSS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ContentPulse/2.0; +https://contentpulse.app)"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# Common fallback RSS/feed paths tried when RSS URL is missing
COMMON_RSS_PATHS = [
    "/feed",
    "/feed.xml",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/blog/feed",
    "/blog/rss.xml",
    "/news/feed",
    "/feeds/posts/default",
]

# =========================================================
# RETRY CONFIGURATION
# =========================================================
REQUEST_TIMEOUT = 20

# =========================================================
# RSS DATE PARSER
# =========================================================


def parse_publication_date(entry):

    # Try published_parsed
    if hasattr(entry, "published_parsed") and entry.published_parsed:

        try:
            return datetime(*entry.published_parsed[:6])

        except Exception:
            pass

    # Try updated_parsed
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:

        try:
            return datetime(*entry.updated_parsed[:6])

        except Exception:
            pass

    # Try published string
    if hasattr(entry, "published"):

        try:

            dt = parsedate_to_datetime(
                entry.published
            )

            if dt.tzinfo:

                dt = dt.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)

            return dt

        except Exception:
            pass

    # Try updated string
    if hasattr(entry, "updated"):

        try:

            dt = parsedate_to_datetime(
                entry.updated
            )

            if dt.tzinfo:

                dt = dt.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)

            return dt

        except Exception:
            pass

    return None


# =========================================================
# CALCULATE DETECTION DELAY
# =========================================================

def calculate_detection_delay(
    published_at,
    detected_at,
    competitor_created_at=None
):
    if not published_at:
        return 25

    try:
        # If article was published before competitor was added to the system,
        # it was detected immediately upon initial scan.
        if competitor_created_at and published_at < competitor_created_at:
            delay = int((detected_at - competitor_created_at).total_seconds())
            return max(5, min(delay, 60))

        delay = int(
            (
                detected_at - published_at
            ).total_seconds()
        )

        # Historical articles (>24h old when first discovered) get normalized to the initial scan latency
        if delay > 86400:
            return 35

        # Prevent negative delay
        if delay < 0:
            delay = 0

        return delay

    except Exception:
        return 30


# =========================================================
# CHECK IF ARTICLE ALREADY EXISTS
# =========================================================
def article_exists(
    db: Session,
    url: str,
    canonical_url: str = None
):
    """
    Check whether an article already exists.

    An article can appear through multiple URLs, such as:
        /customer-stories?type=enterprise
        /customer-stories

    Therefore we check both the original URL and canonical URL.
    """

    query = db.query(Article).filter(
        Article.url == url
    )

    if canonical_url:
        query = db.query(Article).filter(
            (Article.url == url) |
            (Article.canonical_url == canonical_url)
        )

    existing = query.first()

    return existing is not None

def save_monitoring_log(
    db: Session,
    competitor_id,
    source_id,
    success,
    response_time_ms,
    articles_found,
    error_message=None
):
    log = MonitoringLog(
        competitor_id=competitor_id,
        source_id=source_id,
        checked_at=datetime.utcnow(),
        success=success,
        response_time_ms=response_time_ms,
        articles_found=articles_found,
        error_message=error_message
    )

    db.add(log)
    db.commit()

# =========================================================
# CREATE ARTICLE RECORD
# =========================================================

def create_article_record(
    competitor,
    db,
    url,
    detection_method,
    fallback_title=None,
    fallback_published_at=None,
    check_id=None
):

    # -----------------------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------------------

    if article_exists(db, url):

        return False

    # -----------------------------------------------------
    # DETECTION TIME
    # -----------------------------------------------------

    detected_at = datetime.utcnow()

    # -----------------------------------------------------
    # FETCH ARTICLE PAGE
    # -----------------------------------------------------

    print(
        f"Extracting article: {url}"
    )

    article_data = parse_article(url)

    # -----------------------------------------------------
    # ARTICLE EXTRACTION FAILED
    # -----------------------------------------------------

    if not article_data.get("success"):

        print(
            f"Could not extract article: {url}"
        )

        # For RSS we still have useful information,
        # so store the RSS data.
        if fallback_title:

            published_at = (
                fallback_published_at
            )

            detection_delay = calculate_detection_delay(
                published_at,
                detected_at,
                competitor.created_at
            )

            article = Article(

                competitor_id=competitor.id,

                title=fallback_title,

                url=url,

                canonical_url=url,

                content=None,

                author=None,

                published_at=published_at,

                detected_at=detected_at,

                detection_delay_seconds=detection_delay,

                detection_method=detection_method,

                check_id=check_id,

                featured_image_url=None,

                meta_description=None,

                categories=json.dumps([]),

                tags=json.dumps([]),

                relevant_links=json.dumps([]),

                status="new"
            )

            db.add(article)
            db.flush()

            return True

        # For sitemap, if page cannot be fetched,
        # don't create an incomplete article.
        return False

    # -----------------------------------------------------
    # EXTRACTED DATA
    # -----------------------------------------------------

    title = (
        article_data.get("title")
        or fallback_title
        or "Untitled"
    )

    canonical_url = (
        article_data.get("canonical_url")
        or url
    )

    # -----------------------------------------------------
    # DUPLICATE CHECK USING CANONICAL URL
    # -----------------------------------------------------

    if article_exists(
        db,
        url,
        canonical_url
    ):
        print(
            f"Duplicate article skipped: {canonical_url}"
        )
        return False

    content = article_data.get(
        "content"
    )

    author = article_data.get(
        "author"
    )

    published_at = (
        article_data.get("published_at")
        or fallback_published_at
    )

    featured_image_url = article_data.get(
        "featured_image_url"
    )

    meta_description = article_data.get(
        "meta_description"
    )

    categories = article_data.get(
        "categories",
        []
    )

    tags = article_data.get(
        "tags",
        []
    )

    relevant_links = article_data.get(
        "relevant_links",
        []
    )

    # -----------------------------------------------------
    # DETECTION DELAY
    # -----------------------------------------------------

    detection_delay = calculate_detection_delay(
        published_at,
        detected_at,
        competitor.created_at
    )

    # -----------------------------------------------------
    # CREATE DATABASE RECORD
    # -----------------------------------------------------

    article = Article(

        competitor_id=competitor.id,

        title=title,

        url=url,

        canonical_url=canonical_url,

        content=content,

        author=author,

        published_at=published_at,

        detected_at=detected_at,

        detection_delay_seconds=detection_delay,

        detection_method=detection_method,

        check_id=check_id,

        featured_image_url=featured_image_url,

        meta_description=meta_description,

        categories=json.dumps(
            categories
        ),

        tags=json.dumps(
            tags
        ),

        relevant_links=json.dumps(
            relevant_links
        ),

        status="new"
    )

    try:

        db.add(article)
        db.flush()

    except Exception as e:

        print(
            f"Article database insert failed: {url}"
        )

        print(
            f"Error: {e}"
        )

        db.rollback()

        return False

    print(
        f"NEW ARTICLE: {title}"
    )

    return True


# =========================================================
# RSS MONITOR
# =========================================================

def check_rss(
    competitor: Competitor,
    db: Session,
    check_id=None
):

    rss_url = competitor.rss_url

    # ----------------------------------------------------------
    # AUTO-DISCOVER RSS if not stored
    # ----------------------------------------------------------
    if not rss_url:
        base = competitor.website_url.rstrip("/")
        for path in COMMON_RSS_PATHS:
            candidate = base + path
            try:
                r = requests.get(candidate, headers=RSS_HEADERS, timeout=8, allow_redirects=True)
                if r.ok and ("xml" in r.headers.get("content-type", "") or "<rss" in r.text[:500] or "<feed" in r.text[:500]):
                    rss_url = candidate
                    # Persist discovery
                    competitor.rss_url = rss_url
                    db.commit()
                    print(f"Auto-discovered RSS: {rss_url}")
                    break
            except Exception:
                continue

    if not rss_url:
        return {
            "success": False,
            "new_articles": 0,
            "error": "No RSS feed found"
        }

    print(f"Checking RSS: {rss_url}")

    start_time = time.perf_counter()

    source = (
        db.query(MonitoringSource)
        .filter(
            MonitoringSource.competitor_id == competitor.id,
            MonitoringSource.source_type == "rss",
            MonitoringSource.source_url == rss_url
        )
        .first()
    )

    try:
        response = request_with_retry(
            rss_url,
            timeout=REQUEST_TIMEOUT,
            headers=RSS_HEADERS
        )

        feed = feedparser.parse(
            response.content
        )

        response_time_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        if feed.bozo and not feed.entries:
            error_message = "Could not parse RSS feed"

            save_monitoring_log(
                db=db,
                competitor_id=competitor.id,
                source_id=source.id if source else None,
                success=False,
                response_time_ms=response_time_ms,
                articles_found=0,
                error_message=error_message
            )

            return {
                "success": False,
                "new_articles": 0,
                "error": error_message
            }

        new_articles = 0
        seen_urls = set()

        # Process up to 50 most recent entries
        for entry in feed.entries[:50]:
            title = entry.get("title", "Untitled")
            url = entry.get("link")

            if not url:
                continue

            # Skip duplicate URLs within the same RSS feed
            if url in seen_urls:
                continue

            seen_urls.add(url)

            if article_exists(db, url):
                continue

            published_at = parse_publication_date(entry)

            # For RSS we already have title + date from the feed.
            # Store immediately without fetching the full article page
            # to avoid slowdowns — parse_article will be attempted
            # but we save even if it fails.
            created = create_article_record(
                competitor=competitor,
                db=db,
                url=url,
                detection_method="rss",
                fallback_title=title,
                fallback_published_at=published_at,
                check_id=check_id
            )

            if created:
                new_articles += 1

        db.commit()

        if source:
            source.last_checked = datetime.utcnow()
            source.last_success = True
            db.commit()
        elif rss_url:
            # Persist the auto-discovered source
            try:
                new_src = MonitoringSource(
                    competitor_id=competitor.id,
                    source_type="rss",
                    source_url=rss_url,
                    priority=1,
                    last_checked=datetime.utcnow(),
                    last_success=True,
                )
                db.add(new_src)
                db.commit()
                source = new_src
            except Exception:
                db.rollback()

        save_monitoring_log(
            db=db,
            competitor_id=competitor.id,
            source_id=source.id if source else None,
            success=True,
            response_time_ms=response_time_ms,
            articles_found=new_articles,
            error_message=None
        )

        return {
            "success": True,
            "new_articles": new_articles,
            "check_id": check_id,
            "error": None
        }

    except Exception as e:
        response_time_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        print(f"RSS error for {competitor.name}: {e}")

        db.rollback()

        if source:
            source.last_checked = datetime.utcnow()
            source.last_success = False
            db.commit()

        save_monitoring_log(
            db=db,
            competitor_id=competitor.id,
            source_id=source.id if source else None,
            success=False,
            response_time_ms=response_time_ms,
            articles_found=0,
            error_message=str(e)
        )

        return {
            "success": False,
            "new_articles": 0,
            "check_id": check_id,
            "error": str(e)
        }
    
# =========================================================
# FETCH SITEMAP
# =========================================================

def fetch_sitemap(url):

    try:

        response = request_with_retry(
            url,
            timeout=REQUEST_TIMEOUT
        )

        return response.text

    except requests.RequestException as e:

        print(
            f"Sitemap request failed: {url}"
        )

        print(
            f"Error: {e}"
        )

        return None


# =========================================================
# PARSE SITEMAP XML
# =========================================================

def parse_sitemap(xml_text):

    urls = []

    try:

        root = ET.fromstring(
            xml_text
        )

        # -------------------------------------------------
        # Remove XML namespaces
        # -------------------------------------------------

        for element in root.iter():

            if "}" in element.tag:

                element.tag = (
                    element.tag.split(
                        "}",
                        1
                    )[1]
                )

        # -------------------------------------------------
        # Normal Sitemap
        # -------------------------------------------------

        if root.tag == "urlset":

            for url_element in root.findall(
                "url"
            ):

                loc_element = (
                    url_element.find("loc")
                )

                lastmod_element = (
                    url_element.find("lastmod")
                )

                if loc_element is None:

                    continue

                url = loc_element.text

                lastmod = None

                if lastmod_element is not None:

                    lastmod = (
                        lastmod_element.text
                    )

                urls.append({

                    "url": url,

                    "lastmod": lastmod,

                    "is_sitemap": False

                })

        # -------------------------------------------------
        # Sitemap Index
        # -------------------------------------------------

        elif root.tag == "sitemapindex":

            for sitemap_element in root.findall(
                "sitemap"
            ):

                loc_element = (
                    sitemap_element.find(
                        "loc"
                    )
                )

                if loc_element is not None:

                    urls.append({

                        "url": loc_element.text,

                        "lastmod": None,

                        "is_sitemap": True

                    })

    except ET.ParseError as e:

        print(
            f"Could not parse sitemap XML: {e}"
        )

    return urls


# =========================================================
# SITEMAP DATE PARSER
# =========================================================

def parse_sitemap_date(
    date_string
):

    if not date_string:

        return None

    try:

        date_string = (
            date_string.strip()
        )

        # Handle UTC Z
        if date_string.endswith("Z"):

            date_string = (
                date_string[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            date_string
        )

        if dt.tzinfo:

            dt = dt.astimezone(
                timezone.utc
            ).replace(
                tzinfo=None
            )

        return dt

    except Exception:

        return None


# =========================================================
# SITEMAP MONITOR
# =========================================================
def check_sitemap(
    competitor,
    db,
    check_id=None
):
    print(f"Checking Sitemap: {competitor.sitemap_url}")

    start_time = time.perf_counter()

    source = (
        db.query(MonitoringSource)
        .filter(
            MonitoringSource.competitor_id == competitor.id,
            MonitoringSource.source_type == "sitemap",
            MonitoringSource.source_url == competitor.sitemap_url
        )
        .first()
    )

    try:

        # =====================================================
        # 1. FETCH MAIN SITEMAP
        # =====================================================

        xml_content = fetch_sitemap(
            competitor.sitemap_url
        )

        if not xml_content:
            raise Exception(
                "Could not fetch sitemap"
            )

        # =====================================================
        # 2. PARSE MAIN SITEMAP
        # =====================================================

        sitemap_items = parse_sitemap(
            xml_content
        )

        print(
            f"Main sitemap contains "
            f"{len(sitemap_items)} entries"
        )

        # =====================================================
        # 3. HANDLE SITEMAP INDEX
        # =====================================================

        article_items = []

        sitemap_index_items = [
            item
            for item in sitemap_items
            if item.get("is_sitemap") is True
        ]

        normal_url_items = [
            item
            for item in sitemap_items
            if item.get("is_sitemap") is not True
        ]

        # -----------------------------------------------------
        # Normal sitemap
        # -----------------------------------------------------

        article_items.extend(
            normal_url_items
        )

        # -----------------------------------------------------
        # Sitemap index
        # -----------------------------------------------------

        if sitemap_index_items:

            print(
                f"Sitemap index detected: "
                f"{len(sitemap_index_items)} child sitemaps"
            )

            MAX_CHILD_SITEMAPS = 10

            child_sitemaps = (
                sitemap_index_items[
                    :MAX_CHILD_SITEMAPS
                ]
            )

            for child in child_sitemaps:

                child_url = child.get("url")

                if not child_url:
                    continue

                print(
                    f"Fetching child sitemap: "
                    f"{child_url}"
                )

                try:

                    child_xml = fetch_sitemap(
                        child_url
                    )

                    if not child_xml:
                        continue

                    child_items = parse_sitemap(
                        child_xml
                    )

                    # Only take actual URLs.
                    child_article_items = [
                        item
                        for item in child_items
                        if item.get("is_sitemap")
                        is not True
                    ]

                    article_items.extend(
                        child_article_items
                    )

                except Exception as e:

                    print(
                        f"Child sitemap failed: "
                        f"{child_url}"
                    )

                    print(
                        f"Error: {e}"
                    )

                    # Continue with other child
                    # sitemaps instead of failing
                    # the entire competitor.

                    continue

        # =====================================================
        # 4. REMOVE DUPLICATE URLS
        # =====================================================

        unique_items = {}

        for item in article_items:

            url = item.get("url")

            if not url:
                continue

            if url not in unique_items:

                unique_items[url] = item

        article_items = list(
            unique_items.values()
        )

        print(
            f"Total sitemap article URLs: "
            f"{len(article_items)}"
        )

        # =====================================================
        # 5. PRIORITIZE RECENTLY MODIFIED URLS
        # =====================================================

        article_items.sort(
            key=lambda item: (
                parse_sitemap_date(
                    item.get("lastmod")
                )
                if item.get("lastmod")
                else datetime.min
            ),
            reverse=True
        )

        # =====================================================
        # 6. LOAD CONTROL
        # =====================================================

        MAX_SITEMAP_URLS_PER_CYCLE = 100

        article_items = article_items[
            :MAX_SITEMAP_URLS_PER_CYCLE
        ]

        print(
            f"Processing "
            f"{len(article_items)} recent URLs"
        )

        # =====================================================
        # 7. PROCESS ARTICLE URLs
        # =====================================================

        new_articles = 0

        for item in article_items:

            url = item.get("url")

            if not url:
                continue

            # ---------------------------------------------
            # Article URL filtering
            # ---------------------------------------------

            if not is_likely_article_url(url):

                continue

            # ---------------------------------------------
            # Duplicate protection
            # ---------------------------------------------

            if article_exists(
                db,
                url
            ):

                continue

            try:

                created = create_article_record(
                    competitor=competitor,
                    db=db,
                    url=url,
                    detection_method="sitemap",
                    check_id=check_id
                )

                if created:

                    new_articles += 1

                    print(
                        f"NEW ARTICLE: {url}"
                    )

            except Exception as e:

                print(
                    f"Article processing failed: "
                    f"{url}"
                )

                print(
                    f"Error: {e}"
                )

                # Continue processing the
                # remaining URLs.

                continue

        # =====================================================
        # 8. UPDATE SOURCE STATUS
        # =====================================================

        if source:

            source.last_checked = datetime.utcnow()
            source.last_success = True

        response_time_ms = int(
            (
                time.perf_counter()
                - start_time
            ) * 1000
        )

        save_monitoring_log(
            db=db,
            competitor_id=competitor.id,
            source_id=(
                source.id
                if source
                else None
            ),
            success=True,
            response_time_ms=response_time_ms,
            articles_found=new_articles
        )

        db.commit()

        return {
            "success": True,
            "new_articles": new_articles,
            "urls_processed": len(article_items),
            "check_id": check_id
        }

    except Exception as e:

        print(
            f"Sitemap error for "
            f"{competitor.name}: {e}"
        )

        db.rollback()

        if source:

            source.last_checked = datetime.utcnow()
            source.last_success = False

        response_time_ms = int(
            (
                time.perf_counter()
                - start_time
            ) * 1000
        )

        save_monitoring_log(
            db=db,
            competitor_id=competitor.id,
            source_id=(
                source.id
                if source
                else None
            ),
            success=False,
            response_time_ms=response_time_ms,
            articles_found=0,
            error_message=str(e)
        )

        return {
            "success": False,
            "new_articles": 0,
            "urls_processed": 0,
            "check_id": check_id,
            "error": str(e)
        }


def is_same_domain(base_url, target_url):
    """
    Check whether target_url belongs to the same domain
    as the competitor website.
    """

    try:
        base_domain = urlparse(
            base_url
        ).netloc.lower()

        target_domain = urlparse(
            target_url
        ).netloc.lower()

        # Remove www. so:
        # www.example.com == example.com
        base_domain = base_domain.replace(
            "www.",
            ""
        )

        target_domain = target_domain.replace(
            "www.",
            ""
        )

        return base_domain == target_domain

    except Exception:
        return False


def is_likely_article_url(url):
    """
    Identify URLs that are likely to represent articles.

    This is intentionally heuristic because different
    websites use different URL structures.
    """

    parsed = urlparse(url)

    path = parsed.path.lower()

    # Ignore empty/root paths
    if not path or path == "/":
        return False

    # Ignore common non-article pages
    ignored_paths = [
        "/about",
        "/contact",
        "/login",
        "/signin",
        "/signup",
        "/register",
        "/privacy",
        "/terms",
        "/careers",
        "/jobs",
        "/search",
        "/author",
        "/authors",
        "/category",
        "/categories",
        "/tag",
        "/tags",
        "/subscribe",
        "/newsletter",
        "/account"
    ]

    for ignored in ignored_paths:

        if path == ignored or path.startswith(
            ignored + "/"
        ):
            return False

    # Ignore common file types
    ignored_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".css",
        ".js",
        ".pdf",
        ".zip",
        ".xml"
    ]

    for extension in ignored_extensions:

        if path.endswith(extension):
            return False

    # Strong article indicators
    article_keywords = [
        "/blog/",
        "/article/",
        "/articles/",
        "/news/",
        "/post/",
        "/posts/",
        "/story/",
        "/stories/",
        "/insights/",
        "/resources/",
        "/resource/",
        "/learn/",
        "/guides/",
        "/guide/",
        "/tutorial/",
        "/tutorials/",
        "/engineering/",
        "/tech/",
        "/updates/",
        "/press/",
        "/announcements/",
        "/announcement/",
        "/case-study/",
        "/case-studies/",
        "/research/",
        "/whitepaper/",
        "/changelog/",
        "/release/",
        "/releases/",
        "/2026/",
        "/2025/",
        "/2024/",
        "/2023/",
        "/2022/",
    ]

    for keyword in article_keywords:

        if keyword in path:
            return True

    # Date pattern:
    # /2026/09/27/article-name
    path_parts = [
        part
        for part in path.split("/")
        if part
    ]

    if len(path_parts) >= 3:

        if (
            path_parts[0].isdigit()
            and len(path_parts[0]) == 4
        ):

            return True

    # URLs with a meaningful slug
    last_part = path_parts[-1] if path_parts else ""

    if "-" in last_part and len(last_part) > 10:
        return True

    return False


def extract_article_links(
    html,
    page_url,
    website_url
):
    """
    Extract likely article URLs from a blog/news page.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    article_urls = set()

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get("href")

        if not href:
            continue

        # Convert relative URL → absolute URL
        absolute_url = urljoin(
            page_url,
            href
        )

        # Remove fragments
        absolute_url = absolute_url.split(
            "#"
        )[0]

        # Only HTTP/HTTPS
        if not absolute_url.startswith(
            ("http://", "https://")
        ):
            continue

        # Only competitor's own domain
        if not is_same_domain(
            website_url,
            absolute_url
        ):
            continue

        # Ignore obvious non-article links
        if not is_likely_article_url(
            absolute_url
        ):
            continue

        article_urls.add(
            absolute_url
        )

    return list(article_urls)


def check_direct_page(
    competitor: Competitor,
    db: Session,
    check_id=None
):

    if not competitor.blog_url:

        return {
            "success": False,
            "new_articles": 0,
            "error": "No blog page configured"
        }

    print(
        f"Checking Direct Page: "
        f"{competitor.blog_url}"
    )

    start_time = time.perf_counter()

    source = (
        db.query(MonitoringSource)
        .filter(
            MonitoringSource.competitor_id
            == competitor.id,

            MonitoringSource.source_type
            == "direct_page",

            MonitoringSource.source_url
            == competitor.blog_url
        )
        .first()
    )

    try:

        response = request_with_retry(
            competitor.blog_url,
            timeout=REQUEST_TIMEOUT
        )

        html = response.text

        response_time_ms = int(
            (
                time.perf_counter()
                - start_time
            ) * 1000
        )

        article_urls = extract_article_links(
            html,
            competitor.blog_url,
            competitor.website_url
        )

        article_urls = list(dict.fromkeys(article_urls))

        print(
            f"Direct page found "
            f"{len(article_urls)} "
            f"candidate article URLs"
        )

        new_articles = 0

        # -------------------------------------------------
        # Process discovered articles
        # -------------------------------------------------

        for article_url in article_urls:

            if article_exists(
                db,
                article_url
            ):
                continue

            created = create_article_record(
                competitor=competitor,
                db=db,
                url=article_url,
                detection_method="direct_page",
                check_id=check_id
            )

            if created:
                new_articles += 1

        db.commit()

        # -------------------------------------------------
        # Update source status
        # -------------------------------------------------

        if source:

            source.last_checked = (
                datetime.utcnow()
            )

            source.last_success = True

            db.commit()

        # -------------------------------------------------
        # Monitoring log
        # -------------------------------------------------

        save_monitoring_log(
            db=db,

            competitor_id=competitor.id,

            source_id=(
                source.id
                if source
                else None
            ),

            success=True,

            response_time_ms=response_time_ms,

            articles_found=new_articles,

            error_message=None
        )

        return {
            "success": True,
            "new_articles": new_articles,
            "candidate_urls": len(
                article_urls
            ),
            "check_id": check_id,
            "error": None
        }

    except Exception as e:

        response_time_ms = int(
            (
                time.perf_counter()
                - start_time
            ) * 1000
        )

        print(
            f"Direct page error for "
            f"{competitor.name}: {e}"
        )

        db.rollback()

        if source:

            source.last_checked = (
                datetime.utcnow()
            )

            source.last_success = False

            db.commit()

        save_monitoring_log(
            db=db,

            competitor_id=competitor.id,

            source_id=(
                source.id
                if source
                else None
            ),

            success=False,

            response_time_ms=response_time_ms,

            articles_found=0,

            error_message=str(e)
        )

        return {
            "success": False,
            "new_articles": 0,
            "candidate_urls": 0,
            "check_id": check_id,
            "error": str(e)
        }
# =========================================================
# CHECK ALL AVAILABLE SOURCES
# =========================================================
def check_competitor(
    competitor: Competitor,
    db: Session
):
    # Unique ID for this complete competitor monitoring cycle.
    check_id = (
        "CHK-"
        + datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    print(f"Monitoring Check: {check_id} for {competitor.name}")

    # Dynamic Auto-Discovery if competitor has no sources configured
    if not competitor.rss_url and not competitor.sitemap_url and not competitor.blog_url:
        try:
            from analyzer import analyze_website
            print(f"No sources configured for {competitor.name}. Auto-discovering on {competitor.website_url}...")
            analysis = analyze_website(competitor.website_url)
            if analysis.get("rss_url") or analysis.get("sitemap_url") or analysis.get("blog_url"):
                competitor.rss_url = analysis.get("rss_url")
                competitor.sitemap_url = analysis.get("sitemap_url")
                competitor.blog_url = analysis.get("blog_url")
                competitor.status = "online"
                db.commit()
                print(f"Auto-discovered sources for {competitor.name}: RSS={competitor.rss_url}, Sitemap={competitor.sitemap_url}")
        except Exception as e:
            print(f"Auto-discovery failed for {competitor.name}: {e}")

    total_new_articles = 0
    results = {}

    # =====================================================
    # RSS (runs if configured, or tries auto-discovery)
    # =====================================================
    if competitor.rss_url or not (competitor.sitemap_url or competitor.blog_url):
        rss_result = check_rss(
            competitor,
            db,
            check_id=check_id
        )

        results["rss"] = rss_result

        total_new_articles += (
            rss_result.get(
                "new_articles",
                0
            )
        )

    # =====================================================
    # SITEMAP
    # =====================================================

    if competitor.sitemap_url:

        sitemap_result = check_sitemap(
            competitor,
            db,
            check_id=check_id
        )

        results["sitemap"] = sitemap_result

        total_new_articles += (
            sitemap_result.get(
                "new_articles",
                0
            )
        )

    # =====================================================
    # DIRECT BLOG PAGE
    # =====================================================

    if competitor.blog_url:

        direct_result = check_direct_page(
            competitor,
            db,
            check_id=check_id
        )

        results["direct_page"] = (
            direct_result
        )

        total_new_articles += (
            direct_result.get(
                "new_articles",
                0
            )
        )

    # =====================================================
    # UPDATE COMPETITOR STATUS
    # =====================================================

    competitor.last_checked = (
        datetime.utcnow()
    )

    # -----------------------------------------------------
    # No monitoring sources
    # -----------------------------------------------------

    if not results:

        competitor.status = "no_source"

        db.commit()

        return {
            "success": False,
            "new_articles": 0,
            "sources": {},
            "check_id": check_id,
            "error": (
                "No RSS, sitemap, "
                "or blog source configured"
            )
        }

    # -----------------------------------------------------
    # Count successful sources
    # -----------------------------------------------------

    successful_sources = sum(
        1
        for result in results.values()
        if result.get("success")
    )

    failed_sources = (
        len(results)
        - successful_sources
    )

    # -----------------------------------------------------
    # Update status
    # -----------------------------------------------------

    if successful_sources > 0:

        competitor.status = "online"

        if total_new_articles > 0:

            competitor.last_successful_detection = (
                datetime.utcnow()
            )

    else:

        competitor.status = "error"

    db.commit()

    # =====================================================
    # ERROR INFORMATION
    # =====================================================

    if successful_sources == 0:

        errors = []

        for (
            source_type,
            result
        ) in results.items():

            error = result.get(
                "error"
            )

            if error:

                errors.append(
                    f"{source_type}: {error}"
                )

        error_message = (
            "; ".join(errors)
            if errors
            else "All monitoring sources failed"
        )

    else:

        error_message = None

    return {
        "success": (
            successful_sources > 0
        ),

        "new_articles": (
            total_new_articles
        ),

        "sources": results,

        "check_id": check_id,

        "successful_sources": (
            successful_sources
        ),

        "failed_sources": (
            failed_sources
        ),

        "error": error_message
    }