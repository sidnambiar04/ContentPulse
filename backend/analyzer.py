import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Ordered list of common RSS / Atom paths to probe
COMMON_FEED_PATHS = [
    "/feed",
    "/feed.xml",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/blog/feed",
    "/blog/rss.xml",
    "/blog/feed.xml",
    "/news/feed",
    "/feeds/posts/default",   # Blogger
    "/feed/rss2",             # WordPress.com
    "/rss2",
    "/api/rss",
    "/articles.rss",
    "/en/feed",
    "/en/rss",
]

# Common sitemap paths (in priority order)
COMMON_SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap/sitemap.xml",
    "/sitemap-news.xml",
    "/sitemap-posts.xml",
    "/blog-sitemap.xml",
    "/news-sitemap.xml",
    "/wp-sitemap.xml",        # WordPress block editor
    "/page-sitemap.xml",
]

# Blog / news page keywords (text + href match)
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


def fetch_page(url, timeout=12):
    """Fetch a webpage and return its HTML."""
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
    soup = BeautifulSoup(html, "html.parser")

    # <link rel="alternate" type="application/rss+xml" ...>
    for link in soup.find_all("link", attrs={"rel": lambda v: v and "alternate" in v}):
        feed_type = link.get("type", "").lower()
        if "rss" in feed_type or "atom" in feed_type or "feed" in feed_type:
            href = link.get("href")
            if href:
                return urljoin(base_url, href)

    return None


def probe_common_feed_paths(base_url):
    """Try common feed URL patterns and return the first valid one."""
    base = base_url.rstrip("/")
    for path in COMMON_FEED_PATHS:
        candidate = base + path
        try:
            r = requests.get(candidate, headers=HEADERS, timeout=8, allow_redirects=True)
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
                    print(f"Feed discovered by probing: {candidate}")
                    return candidate
        except Exception:
            continue
    return None


def find_sitemap(base_url, html=None):
    """
    Discover sitemap URL from:
    1. robots.txt  →  Sitemap: directive
    2. HTML <link rel='sitemap'>
    3. Common path probing
    """
    base = base_url.rstrip("/")

    # -- robots.txt --
    try:
        r = requests.get(base + "/robots.txt", headers=HEADERS, timeout=8)
        if r.ok:
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    url = line.split(":", 1)[1].strip()
                    if url:
                        return url
    except Exception:
        pass

    # -- <link rel="sitemap"> in HTML --
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("link", attrs={"rel": lambda v: v and "sitemap" in (v if isinstance(v, list) else [v])}):
            href = tag.get("href")
            if href:
                return urljoin(base_url, href)

    # -- probe common paths --
    for path in COMMON_SITEMAP_PATHS:
        candidate = base + path
        try:
            r = requests.get(candidate, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.ok:
                ct = r.headers.get("content-type", "").lower()
                snippet = r.text[:1200]
                if (
                    "xml" in ct
                    or r.text.lstrip().startswith("<?xml")
                    or "<urlset" in snippet
                    or "<sitemapindex" in snippet
                ):
                    return candidate
        except Exception:
            continue

    return None


def find_blog_page(html, base_url):
    """
    Try to find a blog / article / news index page by scanning nav links.
    Returns the URL of the most likely blog index.
    """
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

        # Must be same domain
        try:
            link_domain = urlparse(absolute).netloc.lower().replace("www.", "")
            if link_domain != base_domain:
                continue
        except Exception:
            continue

        candidates.append((score, absolute))

    if not candidates:
        return None

    # Return highest-scoring link
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def analyze_website(website_url):
    """
    Analyze a competitor website and determine available monitoring strategies.
    Discovers RSS/Atom feed, sitemap, and blog page.
    """
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    website_url = website_url.rstrip("/")

    print(f"Analyzing: {website_url}")

    # --------------------------------------------------
    # 1. Fetch homepage
    # --------------------------------------------------
    html = fetch_page(website_url)

    if not html:
        return {
            "success": False,
            "website_url": website_url,
            "rss_url": None,
            "sitemap_url": None,
            "blog_url": None,
            "available_methods": [],
        }

    # --------------------------------------------------
    # 2. Discover RSS / Atom  (HTML tag first, then probe)
    # --------------------------------------------------
    rss_url = find_feed_in_html(html, website_url)
    if not rss_url:
        rss_url = probe_common_feed_paths(website_url)

    # --------------------------------------------------
    # 3. Discover Sitemap
    # --------------------------------------------------
    sitemap_url = find_sitemap(website_url, html=html)

    # --------------------------------------------------
    # 4. Discover Blog / News page
    # --------------------------------------------------
    blog_url = find_blog_page(html, website_url)

    # --------------------------------------------------
    # 5. Build strategy list
    # --------------------------------------------------
    methods = []
    if rss_url:
        methods.append("rss")
    if sitemap_url:
        methods.append("sitemap")
    if blog_url:
        methods.append("direct_page")

    print(f"Analysis complete: RSS={rss_url}, Sitemap={sitemap_url}, Blog={blog_url}")

    return {
        "success": True,
        "website_url": website_url,
        "rss_url": rss_url,
        "sitemap_url": sitemap_url,
        "blog_url": blog_url,
        "available_methods": methods,
    }


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://techcrunch.com"
    result = analyze_website(url)
    print("\nAnalysis Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")