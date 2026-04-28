#!/usr/bin/env python3
"""Minimal HTTP executor for DNAT VM Runtime"""

import http.server
import subprocess
import json
import tempfile
import os
from pathlib import Path

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        body = {
            "ok": True,
            "service": "dnat-executor",
        }
        encoded = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        if self.path != "/execute":
            self.send_error(404)
            return
        
        # Save bundle to temp file
        content_length = int(self.headers.get('Content-Length', 0))
        bundle_dir = Path(__file__).parent / "input"
        bundle_dir.mkdir(exist_ok=True)
        
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', dir=bundle_dir, delete=False) as f:
            f.write(self.rfile.read(content_length))
            bundle_path = f.name
        
        try:
            # Execute VM
            result = subprocess.run(
                ["bash", str(Path(__file__).parent / "vm" / "run-vm.sh"), bundle_path, "8888"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            # Parse result (should be JSON from runner)
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(output).encode())
        
        except subprocess.TimeoutExpired:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "timeout"}).encode())
        
        finally:
            os.unlink(bundle_path)
    
    def log_message(self, format, *args):
        pass  # Silent

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    
    Path(__file__).parent.joinpath("input").mkdir(exist_ok=True)
    Path(__file__).parent.joinpath("output").mkdir(exist_ok=True)
    
    with http.server.HTTPServer(("0.0.0.0", port), Handler) as server:
        print(f"Listening on port {port}, GET /health, POST /execute")
        server.serve_forever()

