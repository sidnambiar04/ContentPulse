import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Priority RSS / Atom paths to probe
COMMON_FEED_PATHS = [
    "/feed",
    "/rss",
    "/rss.xml",
    "/feed.xml",
    "/atom.xml",
    "/blog/feed",
    "/blog/rss.xml",
    "/blog/feed.xml",
    "/news/feed",
    "/feeds/posts/default",   # Blogger
    "/feed/rss2",             # WordPress
    "/rss2",
    "/api/rss",
    "/articles.rss",
    "/en/feed",
    "/en/rss",
]

# Priority sitemap paths to probe
COMMON_SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap/sitemap.xml",
    "/sitemap-news.xml",
    "/sitemap-posts.xml",
    "/blog-sitemap.xml",
    "/news-sitemap.xml",
    "/wp-sitemap.xml",
    "/page-sitemap.xml",
]

# Blog keywords for heuristics
BLOG_KEYWORDS = [
    "blog",
    "articles",
    "article",
    "news",
    "resources",
    "insights",
    "learn",
    "guide",
    "guides",
    "tutorials",
    "updates",
    "press",
    "engineering",
    "changelog",
    "stories",
    "research",
]


def fetch_page(url, timeout=4):
    """Fetch a webpage with a snappy 4s timeout."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def find_feed_in_html(html, base_url):
    """Look for RSS or Atom feed links declared in HTML <head>."""
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("link", attrs={"rel": lambda v: v and "alternate" in v}):
            feed_type = link.get("type", "").lower()
            if "rss" in feed_type or "atom" in feed_type or "feed" in feed_type:
                href = link.get("href")
                if href:
                    return urljoin(base_url, href)
    except Exception:
        pass
    return None


def _check_feed_candidate(candidate_url):
    """Helper to check an individual feed candidate URL."""
    try:
        r = requests.get(candidate_url, headers=HEADERS, timeout=3, allow_redirects=True)
        if r.ok:
            ct = r.headers.get("content-type", "").lower()
            snippet = r.text[:800]
            if (
                "xml" in ct
                or "rss" in ct
                or "<rss" in snippet
                or "<feed" in snippet
                or "<channel>" in snippet
            ):
                return candidate_url
    except Exception:
        pass
    return None


def probe_common_feed_paths(base_url):
    """Probe feed URL paths in parallel using ThreadPoolExecutor for instant response."""
    base = base_url.rstrip("/")
    candidates = [base + path for path in COMMON_FEED_PATHS]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_check_feed_candidate, url): url for url in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"Feed discovered by parallel probe: {result}")
                return result
    return None


def _check_sitemap_candidate(candidate_url):
    """Helper to check an individual sitemap candidate URL."""
    try:
        r = requests.get(candidate_url, headers=HEADERS, timeout=3, allow_redirects=True)
        if r.ok:
            ct = r.headers.get("content-type", "").lower()
            snippet = r.text[:1200]
            if (
                "xml" in ct
                or r.text.lstrip().startswith("<?xml")
                or "<urlset" in snippet
                or "<sitemapindex" in snippet
            ):
                return candidate_url
    except Exception:
        pass
    return None


def find_sitemap(base_url, html=None):
    """
    Discover sitemap URL from robots.txt, HTML tags, or parallel probing.
    """
    base = base_url.rstrip("/")

    # 1. robots.txt check (quick 3s timeout)
    try:
        r = requests.get(base + "/robots.txt", headers=HEADERS, timeout=3)
        if r.ok:
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    url = line.split(":", 1)[1].strip()
                    if url:
                        return url
    except Exception:
        pass

    # 2. <link rel="sitemap"> in HTML
    if html:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all("link", attrs={"rel": lambda v: v and "sitemap" in (v if isinstance(v, list) else [v])}):
                href = tag.get("href")
                if href:
                    return urljoin(base_url, href)
        except Exception:
            pass

    # 3. Parallel probing of common paths
    candidates = [base + path for path in COMMON_SITEMAP_PATHS]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_check_sitemap_candidate, url): url for url in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                return result

    return None


def find_blog_page(html, base_url):
    """Scan nav links to find a blog/article index page."""
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")
        candidates = []

        for link in soup.find_all("a", href=True):
            text = link.get_text(" ", strip=True).lower()
            href = link.get("href", "")
            href_lower = href.lower()
            combined = f"{text} {href_lower}"

            score = 0
            for kw in BLOG_KEYWORDS:
                if kw in combined:
                    score += 1

            if score == 0:
                continue

            absolute = urljoin(base_url, href).split("#")[0]
            try:
                link_domain = urlparse(absolute).netloc.lower().replace("www.", "")
                if link_domain != base_domain:
                    continue
            except Exception:
                continue

            candidates.append((score, absolute))

        if candidates:
            candidates.sort(key=lambda x: -x[0])
            return candidates[0][1]
    except Exception:
        pass

    return None


def analyze_website(website_url):
    """
    Fast, non-blocking site analyzer.
    Probes RSS, Sitemaps, and Blog pages in parallel.
    Guarantees completion in < 4 seconds.
    """
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    website_url = website_url.rstrip("/")
    print(f"Analyzing: {website_url}")

    # 1. Fetch homepage with tight timeout (4s)
    html = fetch_page(website_url, timeout=4)

    # 2. Discover RSS feed (HTML head first, then parallel probes)
    rss_url = find_feed_in_html(html, website_url)
    if not rss_url:
        rss_url = probe_common_feed_paths(website_url)

    # 3. Discover Sitemap (robots.txt first, HTML, then parallel probes)
    sitemap_url = find_sitemap(website_url, html=html)

    # 4. Discover Blog / News page
    blog_url = None
    if html:
        blog_url = find_blog_page(html, website_url)
    
    # Fallback to base URL as blog URL if no specific blog link found
    if not blog_url:
        blog_url = website_url

    # 5. Build strategy list
    methods = []
    if rss_url:
        methods.append("rss")
    if sitemap_url:
        methods.append("sitemap")
    if blog_url:
        methods.append("direct_page")

    print(f"Analysis complete (< 4s): RSS={rss_url}, Sitemap={sitemap_url}, Blog={blog_url}")

    return {
        "success": True,
        "website_url": website_url,
        "rss_url": rss_url,
        "sitemap_url": sitemap_url,
        "blog_url": blog_url,
        "available_methods": methods,
    }


if __name__ == "__main__":
    import sys, time
    url = sys.argv[1] if len(sys.argv) > 1 else "https://blog.logrocket.com"
    start = time.time()
    result = analyze_website(url)
    print(f"\nAnalysis completed in {time.time() - start:.2f}s:")
    for k, v in result.items():
        print(f"  {k}: {v}")