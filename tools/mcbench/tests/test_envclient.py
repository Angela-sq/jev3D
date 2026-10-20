import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import pytest
from PIL import Image

from mcbench.envclient import EnvClient
from mcbench.types import InfraError


def png_b64(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def serve(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class OkHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        frame = np.full((4, 6, 3), 7, dtype=np.uint8)
        payload = {
            "frame": png_b64(frame),
            "info": {"health": 20.0, "echo_n": body.get("n")},
            "trace": [{"health": 20.0}] * body.get("n", 1),
            "terminated": False,
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class FailHandler(OkHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        data = b'{"error": "boom"}'
        self.send_response(500)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def test_step_roundtrip_decodes_png():
    srv, url = serve(OkHandler)
    try:
        out = EnvClient(url).step({"forward": 1}, 3)
        assert out.frame.shape == (4, 6, 3) and out.frame[0, 0, 0] == 7
        assert out.info["echo_n"] == 3
        assert len(out.trace) == 3
        assert out.terminated is False
    finally:
        srv.shutdown()


def test_http_500_raises_infra_env():
    srv, url = serve(FailHandler)
    try:
        with pytest.raises(InfraError) as e:
            EnvClient(url).reset(0, [])
        assert e.value.kind == "env" and "boom" in str(e.value)
    finally:
        srv.shutdown()


def test_connection_refused_raises_infra_env():
    with pytest.raises(InfraError) as e:
        EnvClient("http://127.0.0.1:9", timeout_s=2).health()
    assert e.value.kind == "env"
