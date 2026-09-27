from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from email.utils import format_datetime
import html

HOST = "127.0.0.1"
PORT = 9000

articles = []


def generate_rss():
    items = ""

    for article in articles:
        items += f"""
        <item>
            <title>{html.escape(article["title"])}</title>
            <link>{article["url"]}</link>
            <guid>{article["url"]}</guid>
            <pubDate>{format_datetime(article["published_at"])}</pubDate>
            <description>{html.escape(article["description"])}</description>
        </item>
        """

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>ContentPulse Demo Blog</title>
        <link>http://{HOST}:{PORT}/</link>
        <description>Controlled test website for ContentPulse</description>
        <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
        {items}
    </channel>
</rss>
"""


class DemoHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # Homepage
        if path == "/":
            response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>ContentPulse Demo Blog</title>

                <link rel="alternate"
                      type="application/rss+xml"
                      title="RSS Feed"
                      href="http://{HOST}:{PORT}/rss.xml">
            </head>

            <body>
                <h1>ContentPulse Demo Blog</h1>
                <p>Controlled website for real-time monitoring tests.</p>

                <h2>Articles</h2>
            """

            for article in articles:
                response += f"""
                <article>
                    <h2>
                        <a href="{article['url']}">
                            {html.escape(article['title'])}
                        </a>
                    </h2>
                    <p>{html.escape(article['description'])}</p>
                </article>
                """

            response += """
            </body>
            </html>
            """

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(response.encode())

        # RSS feed
        elif path == "/rss.xml":
            rss = generate_rss()

            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml")
            self.end_headers()
            self.wfile.write(rss.encode())

        # Publish a new article
        elif path == "/publish":
            title = params.get(
                "title",
                ["ContentPulse Test Article"]
            )[0]

            description = params.get(
                "description",
                ["This is a controlled real-time detection test."]
            )[0]

            published_at = datetime.now(timezone.utc)

            article_id = len(articles) + 1

            article_url = (
                f"http://{HOST}:{PORT}/article/{article_id}"
            )

            articles.append({
                "title": title,
                "description": description,
                "published_at": published_at,
                "url": article_url
            })

            response = f"""
            {{
                "success": true,
                "title": "{title}",
                "publication_timestamp": "{published_at.isoformat()}",
                "article_url": "{article_url}"
            }}
            """

            print()
            print("=" * 60)
            print("NEW ARTICLE PUBLISHED")
            print("=" * 60)
            print(f"Title:       {title}")
            print(f"Published:   {published_at.isoformat()}")
            print(f"URL:         {article_url}")
            print("=" * 60)
            print()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.encode())

        # Individual article
        elif path.startswith("/article/"):

            try:
                article_id = int(path.split("/")[-1])
                article = articles[article_id - 1]
            except (ValueError, IndexError):
                self.send_error(404)
                return

            response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{html.escape(article["title"])}</title>

                <meta name="description"
                      content="{html.escape(article["description"])}">

                <link rel="canonical"
                      href="{article["url"]}">
            </head>

            <body>

                <article>

                    <h1>{html.escape(article["title"])}</h1>

                    <p>
                        Published:
                        {article["published_at"].isoformat()}
                    </p>

                    <p>
                        Author: ContentPulse Test Author
                    </p>

                    <div>
                        <p>
                            {html.escape(article["description"])}
                        </p>

                        <p>
                            This article is generated specifically
                            for the ContentPulse real-time monitoring
                            demonstration.
                        </p>
                    </div>

                </article>

            </body>
            </html>
            """

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(response.encode())

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), DemoHandler)

    print("=" * 60)
    print("ContentPulse Controlled Demo Website")
    print("=" * 60)
    print(f"Website:  http://{HOST}:{PORT}")
    print(f"RSS:      http://{HOST}:{PORT}/rss.xml")
    print()
    print("Publish an article using:")
    print(
        f"http://{HOST}:{PORT}/publish"
        "?title=Your+Article+Title"
    )
    print("=" * 60)

    server.serve_forever()