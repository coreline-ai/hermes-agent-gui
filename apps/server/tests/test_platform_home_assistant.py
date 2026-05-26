import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class HAHandler(BaseHTTPRequestHandler):
    calls = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        self.__class__.calls.append({
            "path": self.path,
            "authorization": self.headers.get("authorization"),
            "body": json.loads(raw.decode("utf-8")),
        })
        payload = b'{"context":{"id":"ctx1"}}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        pass


def _start_ha():
    HAHandler.calls = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), HAHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def test_home_assistant_notify_mock_rest(client):
    httpd, base = _start_ha()
    try:
        client("POST", "/api/auth/login", body={"password": "test-pass"})
        status, body = client(
            "POST",
            "/api/messaging/home_assistant/configure",
            body={
                "credentials": {
                    "ha_url": base,
                    "long_lived_token": "ha-token",
                    "notify_service": "notify.mobile_app_phone",
                }
            },
        )
        assert status == 200
        assert body["configured"] is True

        status, body = client("POST", "/api/messaging/home_assistant/test", body={})
        assert status == 200
        assert body["ok"] is True
        assert body["response"]["context"]["id"] == "ctx1"
        assert HAHandler.calls == [
            {
                "path": "/api/services/notify/mobile_app_phone",
                "authorization": "Bearer ha-token",
                "body": {"title": "Hermes Agent GUI", "message": "Home Assistant notification test"},
            }
        ]
    finally:
        httpd.shutdown()
        httpd.server_close()
