"""Host-side relay that keeps the OpenRouter key out of every container.

The forum container needs an LLM for member replies. Instead of getting the key, it posts to this relay at
http://host.docker.internal:<port>/v1/chat/completions; the relay adds the key and forwards to OpenRouter.
The relay binds to the Mac's loopback, which Docker Desktop exposes to containers on the default bridge (the
forum) but not to containers on --internal networks (the agent). It only forwards chat completions for the
reply model with capped max_tokens, so even code running inside the forum container could make only small
reply-model calls and never read the key.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
PATH = "/v1/chat/completions"
ALLOWED_FIELDS = {"messages", "response_format", "max_tokens", "usage"}
MAX_TOKENS = 3000

_lock = threading.Lock()
_port = None


def start(key: str, model: str) -> int:
    """Start the relay once per process (idempotent); returns its port."""
    global _port
    with _lock:
        if _port is not None:
            return _port

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != PATH:
                    return self._send(404, {"error": "not found"})
                try:
                    req = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)))
                except ValueError:
                    return self._send(400, {"error": "bad json"})
                body = {k: v for k, v in req.items() if k in ALLOWED_FIELDS}
                body["model"] = model  # callers can't pick a different (pricier) model
                body["max_tokens"] = min(int(body.get("max_tokens") or MAX_TOKENS), MAX_TOKENS)
                try:
                    r = httpx.post(OPENROUTER, json=body, timeout=60, headers={"Authorization": f"Bearer {key}"})
                    self._send(r.status_code, r.content)
                except httpx.HTTPError as e:
                    self._send(502, {"error": type(e).__name__})

            def _send(self, code, data):
                raw = data if isinstance(data, bytes) else json.dumps(data).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _port = srv.server_address[1]
        return _port
