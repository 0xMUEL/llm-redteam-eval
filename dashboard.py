"""
dashboard.py — Zero-dependency HTTP + SSE server for LLM Red Team Dashboard.
Uses only Python standard library (no Flask/FastAPI required).

Usage:
    python dashboard.py
    # Opens at http://localhost:5001

Run python main.py in a separate terminal to start an evaluation.
The dashboard reads live_state.json written by the orchestrator.
"""

import json
import os
import sys
import time
import threading
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PORT = 5001
LIVE_STATE_PATH = Path(__file__).parent / "live_state.json"
STATIC_DIR      = Path(__file__).parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_live_state() -> dict:
    """Read live_state.json; return empty-ish dict if missing/invalid."""
    try:
        with open(LIVE_STATE_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "eval_id": "",
            "status": "idle",
            "target_model": "",
            "attacker_model": "",
            "total_tasks": 0,
            "completed_tasks": 0,
            "completed": [],
            "current": None,
            "updated_at": None,
        }
    except (json.JSONDecodeError, OSError):
        return {}


def sse_event(data: dict, event: str = "update") -> bytes:
    """Encode a single SSE frame."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class DashboardHandler(BaseHTTPRequestHandler):
    """Handles GET requests for static files, JSON snapshot, and SSE stream."""

    # Silence the default request logging (keep stderr clean)
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(STATIC_DIR / "dashboard.html")

        elif path == "/api/state":
            self._serve_json(read_live_state())

        elif path == "/api/stream":
            self._serve_sse()

        else:
            # Try to serve a static file relative to STATIC_DIR
            file_path = STATIC_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self._serve_file(file_path)
            else:
                self._send_404()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/clear":
            try:
                LIVE_STATE_PATH.unlink(missing_ok=True)
                self._serve_json({"ok": True})
            except Exception as e:
                self._serve_json({"ok": False, "error": str(e)}, status=500)
        else:
            self._send_404()

    # ── Responses ───────────────────────────────────────────────

    def _serve_file(self, file_path: Path):
        try:
            data = file_path.read_bytes()
        except OSError:
            self._send_404()
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_sse(self):
        """
        Long-lived SSE connection.
        Sends an update immediately, then polls live_state.json every second
        and pushes a new event only when updated_at changes.
        Also sends a keepalive comment every second to prevent proxy timeouts.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        # Allow browser connections from any origin
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_updated_at = None

        try:
            # Send initial state
            state = read_live_state()
            self.wfile.write(sse_event(state))
            self.wfile.flush()
            last_updated_at = state.get("updated_at")

            while True:
                time.sleep(1.0)

                state = read_live_state()
                current_updated_at = state.get("updated_at")

                if current_updated_at != last_updated_at:
                    self.wfile.write(sse_event(state))
                    last_updated_at = current_updated_at

                # Keepalive comment (prevents proxy 60s timeout)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected — normal, just stop
            pass
        except Exception as e:
            # Any other error: log and stop gracefully
            print(f"[SSE] Error: {e}", file=sys.stderr)

    def _send_404(self):
        body = b"Not found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    server.allow_reuse_address = True

    print(f"🚀  Dashboard  →  http://localhost:{PORT}")
    print(f"📂  Watching   →  {LIVE_STATE_PATH}")
    print(f"   Run 'python main.py' in a separate terminal to start an eval.\n")
    print(f"   Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[dashboard] Stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
