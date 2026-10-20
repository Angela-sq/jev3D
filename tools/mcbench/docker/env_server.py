"""HTTP wrapper around MineStudio's MinecraftSim. Runs inside the mcbench-env container.

Endpoints (JSON):
  GET  /health                         -> {"ok", "sim", "minestudio"}
  POST /reset   {"seed", "commands"}   -> {"frame", "info", "trace", "terminated"}
  POST /step    {"action", "n"}        -> same shape; frame/info are from the last step
  POST /command {"commands"}           -> same shape (validation only)

Every reset builds a fresh sim (full world restart) so episodes never share a world.
"""

from __future__ import annotations

import base64
import io
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version

import numpy as np
from PIL import Image

from minestudio.simulator.entry import MinecraftSim, check_engine

PORT = 8765
TRACE_KEYS = ("health", "food_level", "player_pos", "damage_dealt", "is_gui_open")
DROP_KEYS = {"pov", "image", "voxels"}

_lock = threading.Lock()
_sim: MinecraftSim | None = None
_noop: dict | None = None


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def png_b64(frame: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(frame).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def slim(info: dict) -> dict:
    return {k: jsonable(info.get(k)) for k in TRACE_KEYS}


def full(info: dict) -> dict:
    return {k: jsonable(v) for k, v in info.items() if k not in DROP_KEYS}


def env_action(action: dict) -> dict:
    a = dict(_noop)
    for k, v in action.items():
        if k == "camera":
            a["camera"] = np.array(v, dtype=np.float32)
        elif k in a:
            a[k] = int(v)
    return a


def out(obs, info, trace, terminated) -> dict:
    return {"frame": png_b64(obs["image"]), "info": full(info), "trace": trace, "terminated": bool(terminated)}


def run_commands(commands: list[str]):
    # Same call as MineStudio's CommandsCallback, then one no-op step for a fresh frame and info.
    for cmd in commands:
        _sim.env.execute_cmd(cmd)
    obs, _, _, _, info = _sim.step(dict(_noop))
    return obs, info


def do_reset(body: dict) -> dict:
    global _sim, _noop
    if _sim is not None:
        try:
            _sim.close()
        except Exception:
            pass
        _sim = None
    _sim = MinecraftSim(action_type="env", obs_size=(640, 360), seed=int(body["seed"]))
    obs, info = _sim.reset()
    _noop = {k: v for k, v in _sim.env.action_space.no_op().items()}
    commands = body.get("commands") or []
    if commands:
        obs, info = run_commands(commands)
    return out(obs, info, [slim(info)], False)


def do_step(body: dict) -> dict:
    a = env_action(body["action"])
    n = int(body.get("n", 1))
    trace, terminated = [], False
    obs = info = None
    for i in range(n):
        step_a = a
        if i > 0 and a.get("inventory"):
            # Inventory is a toggle: press it only on the first step.
            step_a = dict(a, inventory=0)
        obs, _, term, trunc, info = _sim.step(step_a)
        trace.append(slim(info))
        if term or trunc:
            terminated = True
            break
    return out(obs, info, trace, terminated)


def do_command(body: dict) -> dict:
    obs, info = run_commands(body["commands"])
    return out(obs, info, [slim(info)], False)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "sim": _sim is not None, "minestudio": version("minestudio")})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        routes = {"/reset": do_reset, "/step": do_step, "/command": do_command}
        fn = routes.get(self.path)
        if fn is None:
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if fn is not do_reset and _sim is None:
                return self._send(409, {"error": "call /reset first"})
            with _lock:
                payload = fn(body)
            self._send(200, payload)
        except Exception:
            self._send(500, {"error": traceback.format_exc()})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    check_engine(skip_confirmation=True)
    print(f"mcbench env server on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
