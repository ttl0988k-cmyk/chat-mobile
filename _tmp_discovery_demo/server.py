"""Tiny demo server: serves a product list as JSON."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 9191

ITEMS = [
    {"id": 1, "name": "apple"},
    {"id": 2, "name": "banana"},
    {"id": 3, "name": "cherry"},
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/items":
            body = json.dumps(ITEMS).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    print("serving on http://127.0.0.1:%d" % PORT)
    httpd.serve_forever()
