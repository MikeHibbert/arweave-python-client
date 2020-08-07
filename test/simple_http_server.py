from http.server import HTTPServer, BaseHTTPRequestHandler

from io import BytesIO


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Hello, world!')

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'OK')
        self.wfile.write(response.getvalue())


httpd = HTTPServer(('localhost', 80), SimpleHTTPRequestHandler)
httpd.serve_forever()