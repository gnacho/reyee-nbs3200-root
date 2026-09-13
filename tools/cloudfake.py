#!/usr/bin/env python3
"""HTTP falso para observar que pide el switch en cloud_recovery."""
import http.server, socketserver, datetime, sys

LOG = "/tmp/opencode/http-recovery.log"

class H(http.server.BaseHTTPRequestHandler):
    def _log(self):
        with open(LOG, "a") as f:
            f.write("%s %s %s %s\n" % (
                datetime.datetime.now().strftime("%H:%M:%S"),
                self.command, self.path, self.client_address[0]))
            for k, v in self.headers.items():
                f.write("    %s: %s\n" % (k, v))
    def do_GET(self):
        self._log()
        body = b'{"code":0,"recovery_url":"tftp://192.168.64.1/rgos.bin"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_POST = do_GET
    def log_message(self, *a):
        pass

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("0.0.0.0", 80), H) as httpd:
    with open(LOG, "a") as f:
        f.write("=== servidor arriba %s ===\n" % datetime.datetime.now().strftime("%H:%M:%S"))
    httpd.serve_forever()
