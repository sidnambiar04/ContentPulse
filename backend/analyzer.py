import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": "ContentPulse/1.0"
}


def fetch_page(url):
    """Fetch a webpage and return its HTML."""

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        response.raise_for_status()

        return response.text

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def find_feed(html, base_url):
    """Look for RSS or Atom feed links in HTML."""

    soup = BeautifulSoup(html, "html.parser")

    # Look for RSS/Atom <link> elements
    feed_links = soup.find_all(
        "link",
        attrs={
            "rel": lambda value: value and "alternate" in value
        }
    )

    for link in feed_links:
        feed_type = link.get("type", "").lower()

        if (
            "rss" in feed_type
            or "atom" in feed_type
        ):
            href = link.get("href")

            if href:
                return urljoin(base_url, href)

    return None


def find_sitemap(base_url):
    """Look for sitemap using robots.txt and common locations."""

    # First check robots.txt
    robots_url = urljoin(base_url, "/robots.txt")

    try:
        response = requests.get(
            robots_url,
            headers=HEADERS,
            timeout=10
        )

        if response.ok:

            for line in response.text.splitlines():

                if line.lower().startswith("sitemap:"):

                    sitemap_url = line.split(
                        ":",
                        1
                    )[1].strip()

                    if sitemap_url:
                        return sitemap_url

    except requests.RequestException:
        pass

    # Try common sitemap locations
    possible_sitemaps = [
        "/sitemap.xml",
        "/sitemap_index.xml"
    ]

    for path in possible_sitemaps:

        sitemap_url = urljoin(
            base_url,
            path
        )

        try:
            response = requests.get(
                sitemap_url,
                headers=HEADERS,
                timeout=10
            )

            if response.ok:

                content_type = response.headers.get(
                    "content-type",
                    ""
                ).lower()

                if (
                    "xml" in content_type
                    or response.text.lstrip().startswith("<?xml")
                    or "<urlset" in response.text[:1000]
                    or "<sitemapindex" in response.text[:1000]
                ):
                    return sitemap_url

        except requests.RequestException:
            continue

    return None


def find_blog_page(html, base_url):
    """Try to find a blog/article/news page."""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    keywords = [
        "blog",
        "articles",
        "news",
        "resources",
        "insights"
    ]

    links = soup.find_all("a", href=True)

    for link in links:

        text = link.get_text(
            " ",
            strip=True
        ).lower()

        href = link.get("href", "")

        combined = f"{text} {href.lower()}"

        for keyword in keywords:

            if keyword in combined:

                return urljoin(
                    base_url,
                    href
                )

    return None


def analyze_website(website_url):
    """
    Analyze a competitor website and determine
    available monitoring strategies.
    """

    # Make sure URL ends correctly
    if not website_url.startswith(
        ("http://", "https://")
    ):
        website_url = "https://" + website_url

    # Remove trailing slash
    website_url = website_url.rstrip("/")

    print(f"Analyzing: {website_url}")

    # ------------------------------------------------
    # 1. Fetch homepage
    # ------------------------------------------------

    html = fetch_page(website_url)

    if not html:

        return {
            "success": False,
            "website_url": website_url,
            "rss_url": None,
            "sitemap_url": None,
            "blog_url": None,
            "available_methods": []
        }

    # ------------------------------------------------
    # 2. Find RSS / Atom
    # ------------------------------------------------

    rss_url = find_feed(
        html,
        website_url
    )

    # ------------------------------------------------
    # 3. Find Sitemap
    # ------------------------------------------------

    sitemap_url = find_sitemap(
        website_url
    )

    # ------------------------------------------------
    # 4. Find Blog / Article page
    # ------------------------------------------------

    blog_url = find_blog_page(
        html,
        website_url
    )

    # ------------------------------------------------
    # 5. Determine available strategies
    # ------------------------------------------------

    methods = []

    if rss_url:
        methods.append("rss")

    if sitemap_url:
        methods.append("sitemap")

    if blog_url:
        methods.append("direct_page")

    return {
        "success": True,
        "website_url": website_url,
        "rss_url": rss_url,
        "sitemap_url": sitemap_url,
        "blog_url": blog_url,
        "available_methods": methods
    }

if __name__ == "__main__":

    result = analyze_website(
        "https://example.com"
    )

    print("\nAnalysis Result:")
    print(result)