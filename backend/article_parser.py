import json

from bs4 import BeautifulSoup
from http_utils import request_with_retry
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": "ContentPulse/1.0",
    "Accept": "text/html,application/xhtml+xml"
}


# =========================================================
# FETCH ARTICLE PAGE
# =========================================================

# =========================================================
# FETCH ARTICLE PAGE
# =========================================================

def fetch_article(url):

    try:
        response = request_with_retry(
            url,
            timeout=15
        )

        return response.text

    except Exception as e:

        print(f"Article fetch failed: {url}")
        print(f"Error: {e}")

        return None


# =========================================================
# DATE PARSER
# =========================================================

def parse_date(value):

    if not value:
        return None

    try:
        value = str(value).strip()

        # ISO format
        value = value.replace("Z", "+00:00")

        dt = datetime.fromisoformat(value)

        if dt.tzinfo:
            dt = dt.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        return dt

    except Exception:
        pass

    try:

        dt = parsedate_to_datetime(
            str(value)
        )

        if dt.tzinfo:
            dt = dt.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        return dt

    except Exception:
        return None


# =========================================================
# JSON-LD EXTRACTION
# =========================================================

def extract_json_ld(soup):

    objects = []

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        try:

            raw = (
                script.string
                or script.get_text()
            )

            if not raw.strip():
                continue

            data = json.loads(raw)

            if isinstance(data, list):

                objects.extend(data)

            else:

                objects.append(data)

        except Exception:

            continue

    return objects


# =========================================================
# FIND ARTICLE SCHEMA
# =========================================================

def find_article_schema(json_objects):

    article_types = {
        "Article",
        "NewsArticle",
        "BlogPosting"
    }

    for obj in json_objects:

        if not isinstance(obj, dict):
            continue

        # ---------------------------------------------
        # Direct JSON-LD object
        # ---------------------------------------------

        obj_type = obj.get("@type")

        if isinstance(obj_type, list):

            types = obj_type

        else:

            types = [obj_type]

        if any(
            t in article_types
            for t in types
        ):

            return obj

        # ---------------------------------------------
        # JSON-LD @graph
        # ---------------------------------------------

        graph = obj.get("@graph")

        if isinstance(graph, list):

            for item in graph:

                if not isinstance(item, dict):
                    continue

                item_type = item.get(
                    "@type"
                )

                if isinstance(item_type, list):

                    types = item_type

                else:

                    types = [item_type]

                if any(
                    t in article_types
                    for t in types
                ):

                    return item

    return None


# =========================================================
# TITLE
# =========================================================

def extract_title(
    soup,
    article_schema
):

    # JSON-LD
    if article_schema:

        title = article_schema.get(
            "headline"
        )

        if title:
            return str(title).strip()

    # OpenGraph
    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title:

        content = og_title.get(
            "content"
        )

        if content:
            return content.strip()

    # H1
    h1 = soup.find("h1")

    if h1:

        title = h1.get_text(
            " ",
            strip=True
        )

        if title:
            return title

    # HTML title
    title_tag = soup.find("title")

    if title_tag:

        title = title_tag.get_text(
            " ",
            strip=True
        )

        if title:
            return title

    return "Untitled"


# =========================================================
# AUTHOR
# =========================================================

def extract_author(
    soup,
    article_schema
):

    if article_schema:

        author = article_schema.get(
            "author"
        )

        # author = {"name": "..."}
        if isinstance(author, dict):

            name = author.get("name")

            if name:
                return str(name).strip()

        # author = [{"name": "..."}]
        elif isinstance(author, list):

            names = []

            for item in author:

                if isinstance(item, dict):

                    name = item.get("name")

                    if name:
                        names.append(
                            str(name).strip()
                        )

                elif isinstance(item, str):

                    names.append(
                        item.strip()
                    )

            if names:
                return ", ".join(names)

        # author = "John"
        elif isinstance(author, str):

            return author.strip()

    # Meta author
    meta_author = soup.find(
        "meta",
        attrs={"name": "author"}
    )

    if meta_author:

        value = meta_author.get(
            "content"
        )

        if value:
            return value.strip()

    # Common HTML selectors
    author_element = soup.select_one(
        ".author, .byline, [rel='author']"
    )

    if author_element:

        value = author_element.get_text(
            " ",
            strip=True
        )

        if value:
            return value

    return None


# =========================================================
# PUBLICATION DATE
# =========================================================

def extract_publication_date(
    soup,
    article_schema
):

    # JSON-LD
    if article_schema:

        for field in [
            "datePublished",
            "dateCreated",
            "dateModified"
        ]:

            value = article_schema.get(
                field
            )

            parsed = parse_date(value)

            if parsed:
                return parsed

    # Meta tags
    selectors = [

        {
            "property":
                "article:published_time"
        },

        {
            "property":
                "article:modified_time"
        },

        {
            "name":
                "date"
        },

        {
            "name":
                "publish_date"
        },

        {
            "name":
                "published_time"
        },

        {
            "name":
                "datePublished"
        }
    ]

    for attrs in selectors:

        tag = soup.find(
            "meta",
            attrs=attrs
        )

        if tag:

            value = tag.get(
                "content"
            )

            parsed = parse_date(value)

            if parsed:
                return parsed

    # <time datetime="">
    time_tag = soup.find(
        "time",
        datetime=True
    )

    if time_tag:

        parsed = parse_date(
            time_tag.get("datetime")
        )

        if parsed:
            return parsed

    return None


# =========================================================
# META DESCRIPTION
# =========================================================

def extract_description(
    soup,
    article_schema
):

    # JSON-LD
    if article_schema:

        description = article_schema.get(
            "description"
        )

        if description:
            return str(
                description
            ).strip()

    # Standard description
    meta = soup.find(
        "meta",
        attrs={
            "name": "description"
        }
    )

    if meta:

        value = meta.get(
            "content"
        )

        if value:
            return value.strip()

    # OpenGraph
    og_description = soup.find(
        "meta",
        property="og:description"
    )

    if og_description:

        value = og_description.get(
            "content"
        )

        if value:
            return value.strip()

    return None


# =========================================================
# CANONICAL URL
# =========================================================

def extract_canonical(
    soup,
    original_url
):

    canonical = soup.find(
        "link",
        rel=lambda value:
        value and "canonical" in value
    )

    if canonical:

        href = canonical.get(
            "href"
        )

        if href:

            return urljoin(
                original_url,
                href
            )

    return original_url


# =========================================================
# FEATURED IMAGE
# =========================================================

def extract_image(
    soup,
    article_schema,
    original_url
):

    # JSON-LD
    if article_schema:

        image = article_schema.get(
            "image"
        )

        # String
        if isinstance(image, str):

            return urljoin(
                original_url,
                image
            )

        # Dictionary
        if isinstance(image, dict):

            image_url = image.get(
                "url"
            )

            if image_url:

                return urljoin(
                    original_url,
                    image_url
                )

        # List
        if isinstance(image, list):

            for item in image:

                if isinstance(
                    item,
                    str
                ):

                    return urljoin(
                        original_url,
                        item
                    )

                if isinstance(
                    item,
                    dict
                ):

                    image_url = item.get(
                        "url"
                    )

                    if image_url:

                        return urljoin(
                            original_url,
                            image_url
                        )

    # OpenGraph image
    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:

        image_url = og_image.get(
            "content"
        )

        if image_url:

            return urljoin(
                original_url,
                image_url
            )

    return None


# =========================================================
# CATEGORIES AND TAGS
# =========================================================

def extract_categories_and_tags(
    soup,
    article_schema=None
):

    categories = []
    tags = []

    # JSON-LD Schema
    if article_schema:
        section = article_schema.get("articleSection")
        if isinstance(section, list):
            for s in section:
                if s and str(s).strip():
                    categories.append(str(s).strip())
        elif isinstance(section, str) and section.strip():
            categories.append(section.strip())

        keywords = article_schema.get("keywords")
        if isinstance(keywords, list):
            for k in keywords:
                if k and str(k).strip():
                    tags.append(str(k).strip())
        elif isinstance(keywords, str) and keywords.strip():
            for k in keywords.split(","):
                if k.strip():
                    tags.append(k.strip())

    # article:section
    for element in soup.find_all(
        "meta",
        attrs={"property": ["article:section", "og:article:section"]}
    ):
        value = element.get("content")
        if value and value.strip():
            categories.append(value.strip())

    # article:tag
    for element in soup.find_all(
        "meta",
        attrs={"property": ["article:tag", "og:article:tag"]}
    ):
        value = element.get("content")
        if value and value.strip():
            tags.append(value.strip())

    # meta keywords
    meta_keywords = soup.find(
        "meta",
        attrs={"name": "keywords"}
    )
    if meta_keywords:
        kw = meta_keywords.get("content", "")
        if kw:
            for k in kw.split(","):
                if k.strip():
                    tags.append(k.strip())

    # Category links
    for element in soup.select(
        ".category a, "
        ".categories a, "
        "[rel='category']"
    ):
        value = element.get_text(
            " ",
            strip=True
        )
        if value:
            categories.append(value)

    # Tag links
    for element in soup.select(
        ".tag a, "
        ".tags a, "
        "[rel='tag']"
    ):
        value = element.get_text(
            " ",
            strip=True
        )
        if value:
            tags.append(value)

    # Remove duplicates
    categories = list(
        dict.fromkeys(
            categories
        )
    )

    tags = list(
        dict.fromkeys(
            tags
        )
    )

    return categories, tags


# =========================================================
# ARTICLE BODY
# =========================================================

def extract_body(soup):

    # Remove elements that are usually
    # not part of article content
    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header"
        ]
    ):

        element.decompose()

    # ---------------------------------------------
    # Semantic <article>
    # ---------------------------------------------

    article = soup.find(
        "article"
    )

    if article:

        text = article.get_text(
            "\n",
            strip=True
        )

        if len(text) > 100:

            return text

    # ---------------------------------------------
    # Common article containers
    # ---------------------------------------------

    selectors = [

        "main",

        ".article-content",

        ".article-body",

        ".post-content",

        ".entry-content",

        ".blog-post",

        ".post",

        ".content"
    ]

    for selector in selectors:

        element = soup.select_one(
            selector
        )

        if element:

            text = element.get_text(
                "\n",
                strip=True
            )

            if len(text) > 200:

                return text

    return ""


# =========================================================
# RELEVANT LINKS
# =========================================================

def extract_links(
    soup,
    original_url
):

    links = []

    # Prefer article container
    article = soup.find(
        "article"
    )

    container = (
        article
        if article
        else soup
    )

    for link in container.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href"
        )

        if not href:
            continue

        href_lower = href.strip().lower()
        if href_lower.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        absolute_url = urljoin(
            original_url,
            href
        )

        text = link.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        links.append({

            "text": text,

            "url": absolute_url

        })

    # Remove duplicates
    unique_links = []
    seen = set()

    for link in links:

        if link["url"] in seen:
            continue

        seen.add(
            link["url"]
        )

        unique_links.append(
            link
        )

    return unique_links


# =========================================================
# MAIN ARTICLE PARSER
# =========================================================

def parse_article(url):

    print(
        f"Extracting article: {url}"
    )

    html = fetch_article(
        url
    )

    if not html:

        return {

            "success": False,

            "url": url,

            "error":
                "Could not fetch article"

        }

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ---------------------------------------------
    # JSON-LD
    # ---------------------------------------------

    json_objects = extract_json_ld(
        soup
    )

    article_schema = find_article_schema(
        json_objects
    )

    # ---------------------------------------------
    # Extract fields
    # ---------------------------------------------

    title = extract_title(
        soup,
        article_schema
    )

    author = extract_author(
        soup,
        article_schema
    )

    published_at = extract_publication_date(
        soup,
        article_schema
    )

    meta_description = extract_description(
        soup,
        article_schema
    )

    canonical_url = extract_canonical(
        soup,
        url
    )

    featured_image_url = extract_image(
        soup,
        article_schema,
        url
    )

    categories, tags = (
        extract_categories_and_tags(
            soup,
            article_schema
        )
    )

    content = extract_body(
        soup
    )

    relevant_links = extract_links(
        soup,
        url
    )

    # ---------------------------------------------
    # Return result
    # ---------------------------------------------

    return {

        "success": True,

        "url": url,

        "title": title,

        "content": content,

        "author": author,

        "published_at": published_at,

        "canonical_url": canonical_url,

        "featured_image_url":
            featured_image_url,

        "meta_description":
            meta_description,

        "categories":
            categories,

        "tags":
            tags,

        "relevant_links":
            relevant_links,

        "error": None
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_url = (
        "https://news.ycombinator.com/"
    )

    result = parse_article(
        test_url
    )

    print("\nRESULT:\n")

    print(
        json.dumps(
            result,
            indent=4,
            default=str
        )
    )