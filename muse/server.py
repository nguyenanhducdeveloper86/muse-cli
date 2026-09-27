import sys
import os
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from muse.core import MuseClient


class BridgeHandler(BaseHTTPRequestHandler):
    client = None

    def log_message(self, fmt, *args):
        pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/v1/models", "/models"):
            self._json({
                "object": "list",
                "data": [
                    {
                        "id": "muse-ai",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "muse.ai"
                    }
                ]
            })
            return
        if p in ("/", "/health"):
            self._json({"status": "running", "service": "muse.ai Bridge Server"})
            return
        self._json({"error": "Not found"}, 404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p in ("/v1/chat/completions", "/chat/completions"):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                req = json.loads(raw)
            except Exception:
                self._json({"error": "Invalid JSON"}, 400)
                return

            messages = req.get("messages", [])
            prompt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    prompt = m.get("content", "")
                    break

            if not prompt:
                self._json({"error": "No user message found"}, 400)
                return

            print(f"  [Bridge] Nhận request: {prompt[:60]}...")
            if not BridgeHandler.client:
                BridgeHandler.client = MuseClient(headless=True)

            res = BridgeHandler.client.chat(prompt)
            if not res.get("ok"):
                self._json({"error": res.get("error", "Unknown error")}, 500)
                return

            reply = res.get("reply", "")
            print(f"  [Bridge] Trả lời: {reply[:60]}...")

            cmpl_id = f"chatcmpl-muse-{uuid.uuid4().hex[:12]}"
            created = int(time.time())

            response_data = {
                "id": cmpl_id,
                "object": "chat.completion",
                "created": created,
                "model": "muse-ai",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": reply
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(reply.split()),
                    "total_tokens": len(prompt.split()) + len(reply.split())
                }
            }
            self._json(response_data)
            return

        self._json({"error": "Not found"}, 404)


def run_server(host="127.0.0.1", port=8765):
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), BridgeHandler)
    print("=" * 60)
    print(f"  🚀 Muse.ai OpenAI-Compatible Bridge Server")
    print("=" * 60)
    print(f"  API Endpoint:  http://{host}:{port}/v1")
    print(f"  Model ID:      muse-ai")
    print("=" * 60)
    print("  Đang khởi tạo trình duyệt kết nối ngầm...")
    BridgeHandler.client = MuseClient(headless=True)
    print("  ✅ Sẵn sàng nhận request từ omp / Cursor / Cline / curl!")
    print("  Bấm Ctrl+C để dừng.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng server...")
        server.server_close()
        if BridgeHandler.client:
            BridgeHandler.client.close()
