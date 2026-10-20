"""HTTP client for the mcbench env server (docker/env_server.py)."""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

import numpy as np
from PIL import Image

from mcbench.types import InfraError


@dataclass
class StepOut:
    frame: np.ndarray
    info: dict
    trace: list[dict]
    terminated: bool


def decode_frame(b64: str) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))


@dataclass
class EnvClient:
    url: str = "http://127.0.0.1:8765"
    timeout_s: float = 300.0

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.url + path, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[-2000:]
            raise InfraError("env", f"HTTP {e.code} on {path}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise InfraError("env", f"{path}: {e}") from e

    def _step_out(self, r: dict) -> StepOut:
        return StepOut(decode_frame(r["frame"]), r["info"], r.get("trace", []), bool(r.get("terminated")))

    def health(self) -> bool:
        return bool(self._call("GET", "/health").get("ok"))

    def reset(self, seed: int, commands: list[str]) -> StepOut:
        return self._step_out(self._call("POST", "/reset", {"seed": seed, "commands": commands}))

    def step(self, env_action: dict, n: int) -> StepOut:
        return self._step_out(self._call("POST", "/step", {"action": env_action, "n": n}))

    def command(self, commands: list[str]) -> StepOut:
        return self._step_out(self._call("POST", "/command", {"commands": commands}))
