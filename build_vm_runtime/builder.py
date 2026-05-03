#!/usr/bin/env python3
"""Minimal HTTP builder for isolated DNAT application artifact builds."""

import http.server
import json
import os
import subprocess
import tempfile
from pathlib import Path


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        body = {
            "ok": True,
            "service": "dnat-builder",
        }
        encoded = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        if self.path != "/build":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        bundle_dir = Path(__file__).parent / "input"
        bundle_dir.mkdir(exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", dir=bundle_dir, delete=False) as bundle_file:
            bundle_file.write(self.rfile.read(content_length))
            bundle_path = bundle_file.name

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", dir=bundle_dir, delete=False) as output_file:
            output_bundle_path = output_file.name

        try:
            result = subprocess.run(
                ["bash", str(Path(__file__).parent / "vm" / "build-vm.sh"), bundle_path, output_bundle_path],
                capture_output=True,
                text=True,
                timeout=2400,
            )

            if result.returncode != 0:
                try:
                    payload = json.loads(result.stdout or result.stderr)
                except json.JSONDecodeError:
                    payload = {
                        "error": "builder failed",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }

                encoded = json.dumps(payload).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            data = Path(output_bundle_path).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        except subprocess.TimeoutExpired:
            encoded = json.dumps({"error": "builder timeout"}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        finally:
            os.unlink(bundle_path)
            if os.path.exists(output_bundle_path):
                os.unlink(output_bundle_path)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5100
    Path(__file__).parent.joinpath("input").mkdir(exist_ok=True)

    with http.server.HTTPServer(("0.0.0.0", port), Handler) as server:
        print(f"Listening on port {port}, GET /health, POST /build")
        server.serve_forever()
