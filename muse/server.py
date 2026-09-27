import sys
import os
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from muse.core import MuseClient


def extract_text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif "content" in part:
                    parts.append(extract_text_content(part["content"]))
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


class BridgeHandler(BaseHTTPRequestHandler):
    client = None

    def log_message(self, fmt, *args):
        pass

    def _json(self, data, status=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"  [Bridge] Lỗi khi ghi response: {e}", file=sys.stderr)
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
        if p in ("/", "/health", "/status"):
            is_ready = bool(BridgeHandler.client and BridgeHandler.client.is_ready)
            self._json({"ok": True, "status": "running", "service": "muse.ai Bridge Server", "ready": is_ready})
            return
        self._json({"error": "Not found"}, 404)

    def do_POST(self):
        try:
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
                        prompt = extract_text_content(m.get("content", ""))
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

            if p in ("/api/ask",):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    req = json.loads(raw)
                except Exception:
                    self._json({"error": "Invalid JSON"}, 400)
                    return
                prompt = extract_text_content(req.get("prompt", ""))
                timeout = int(req.get("timeout", 60))
                if not prompt:
                    self._json({"error": "prompt is required"}, 400)
                    return
                if not BridgeHandler.client:
                    BridgeHandler.client = MuseClient(headless=True)
                res = BridgeHandler.client.chat(prompt, timeout=timeout)
                self._json(res, 200 if res.get("ok") else 500)
                return

            if p in ("/api/generate-image", "/v1/images/generations"):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    req = json.loads(raw)
                except Exception:
                    self._json({"error": "Invalid JSON"}, 400)
                    return
                prompt = extract_text_content(req.get("prompt", ""))
                out_path = req.get("out_path") or req.get("output_path")
                ref_image = req.get("ref_image") or req.get("image")
                timeout = int(req.get("timeout", 90))
                if not prompt:
                    self._json({"error": "prompt is required"}, 400)
                    return
                if not BridgeHandler.client:
                    BridgeHandler.client = MuseClient(headless=True)
                res = BridgeHandler.client.image(prompt, out_path=out_path, ref_image=ref_image, timeout=timeout)
                self._json(res, 200 if res.get("ok") else 500)
                return

            if p in ("/api/generate-video", "/v1/videos/generations"):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    req = json.loads(raw)
                except Exception:
                    self._json({"error": "Invalid JSON"}, 400)
                    return
                prompt = extract_text_content(req.get("prompt", ""))
                out_path = req.get("out_path") or req.get("output_path")
                ref_image = req.get("ref_image") or req.get("image")
                timeout = int(req.get("timeout", 120))
                if not prompt:
                    self._json({"error": "prompt is required"}, 400)
                    return
                if not BridgeHandler.client:
                    BridgeHandler.client = MuseClient(headless=True)
                res = BridgeHandler.client.video(prompt, out_path=out_path, ref_image=ref_image, timeout=timeout)
                self._json(res, 200 if res.get("ok") else 500)
                return

            self._json({"error": "Not found"}, 404)
        except Exception as e:
            print(f"  [Bridge] Ngoại lệ không xử lý trong do_POST: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            try:
                self._json({"error": f"Internal server error: {e}"}, 500)
            except Exception:
                pass

def run_server(host="127.0.0.1", port=None):
    if port is None:
        port = int(os.environ.get("MUSE_PORT", 8766))
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
