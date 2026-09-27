from http.server import BaseHTTPRequestHandler, HTTPServer
import time

HOST = "127.0.0.1"
PORT = 9001


class SlowHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/slow":

            print("Slow request received...")
            print("Sleeping for 20 seconds...")

            time.sleep(20)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"""
                <html>
                    <head>
                        <title>Slow Test Site</title>
                    </head>
                    <body>
                        <h1>Slow Test Site</h1>
                        <p>This response intentionally takes 20 seconds.</p>
                    </body>
                </html>
                """
            )

        else:

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"""
                <html>
                    <body>
                        <h1>Slow Test Site</h1>
                    </body>
                </html>
                """
            )

    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}")


if __name__ == "__main__":

    server = HTTPServer(
        (HOST, PORT),
        SlowHandler
    )

    print("=" * 60)
    print("ContentPulse Slow Test Site")
    print("=" * 60)
    print(f"Website: http://{HOST}:{PORT}")
    print(f"Slow URL: http://{HOST}:{PORT}/slow")
    print("=" * 60)

    server.serve_forever()