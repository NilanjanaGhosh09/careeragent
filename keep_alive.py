from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CareerAgent is alive")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *args):
        pass

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
