"""Fable 5.1 agent, called through `claude -p` on a Claude subscription.

Each decision is one fresh `claude -p` process with every tool, MCP server, setting
file, and the default system prompt stripped, so a call costs about 1k tokens instead
of about 31k. The screenshot goes in as a base64 PNG content block over stream-json.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image

from mcbench.timing import STEPS_PER_SECOND
from mcbench.types import KEYS, Action, ActMeta, InfraError, Observation

MODEL = "claude-fable-5-1"
PROMPT_PATH = Path(__file__).with_name("fable_prompt.md")
MAX_HOLD_STEPS = 100  # "duration" is capped at 5 s

RATE_LIMIT_RE = re.compile(r"rate.?limit|usage limit|limit reached|\b429\b|overloaded|too many requests", re.I)
AUTH_RE = re.compile(r"\bauth|/login|log ?in|api key|unauthori[sz]ed|\b401\b", re.I)

Runner = Callable[[list[str], str, dict, float], tuple[int, str, str]]


def subprocess_env() -> dict:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def default_runner(args: list[str], stdin: str, env: dict, timeout: float) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, input=stdin, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise InfraError("cli", f"claude -p timed out after {timeout}s") from e
    return p.returncode, p.stdout, p.stderr


def check_auth() -> dict:
    """Require that `claude` is logged in through claude.ai (the subscription)."""
    p = subprocess.run(
        [shutil.which("claude") or "claude", "auth", "status"],
        capture_output=True, text=True, env=subprocess_env(), timeout=60,
    )
    try:
        status = json.loads(p.stdout)
    except ValueError as e:
        raise InfraError("auth", f"could not read `claude auth status`: {p.stdout[:300]} {p.stderr[:300]}", True) from e
    if not status.get("loggedIn") or status.get("authMethod") != "claude.ai":
        raise InfraError("auth", f"expected subscription login (authMethod claude.ai), got {status}", True)
    return status


def parse_action(text: str) -> tuple[Action, bool]:
    """Return (action, format_error). Uses the last JSON object in the text."""
    dec = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict):
                found = obj
    if found is None:
        return Action.noop(), True
    try:
        keys = found.get("keys", [])
        if not isinstance(keys, list):
            raise TypeError("keys must be a list")
        hotbar = found.get("hotbar")
        if hotbar is not None:
            hotbar = int(hotbar)
            if not 1 <= hotbar <= 9:
                hotbar = None
        duration = found.get("duration")
        hold = None
        if duration is not None:
            hold = min(MAX_HOLD_STEPS, max(1, round(float(duration) * STEPS_PER_SECOND)))
        a = Action(
            keys=frozenset(k for k in keys if k in KEYS),
            yaw=float(found.get("yaw", 0) or 0),
            pitch=float(found.get("pitch", 0) or 0),
            attack=bool(found.get("attack", False)),
            click=bool(found.get("click", False)),
            use=bool(found.get("use", False)),
            hotbar=hotbar,
            inventory=bool(found.get("inventory", False)),
            hold_steps=hold,
        )
    except (TypeError, ValueError):
        return Action.noop(), True
    return a, False


def classify_result(event: dict | None, stderr: str) -> dict:
    """Raise InfraError for anything that is not a usable model reply."""
    if event is None:
        blob = stderr[-1000:]
        if RATE_LIMIT_RE.search(blob):
            raise InfraError("rate_limit", blob, True)
        if AUTH_RE.search(blob):
            raise InfraError("auth", blob, True)
        raise InfraError("cli", f"no result event from claude -p: {blob}")
    if event.get("is_error") or event.get("subtype") != "success":
        blob = f"{event.get('result', '')} {stderr[-500:]}"
        if RATE_LIMIT_RE.search(blob):
            raise InfraError("rate_limit", blob, True)
        if AUTH_RE.search(blob):
            raise InfraError("auth", blob, True)
        raise InfraError("cli", f"claude -p error: {blob[:500]}")
    models = list((event.get("modelUsage") or {}).keys())
    if models != [MODEL]:
        raise InfraError("model_identity", f"expected only {MODEL}, got {models}", True)
    return event


def png_b64(frame) -> str:
    buf = io.BytesIO()
    Image.fromarray(frame).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def action_text(a: Action) -> str:
    parts = [",".join(sorted(a.keys)) or "no keys"]
    if a.yaw or a.pitch:
        parts.append(f"turn yaw {a.yaw:+.0f} pitch {a.pitch:+.0f}")
    for flag in ("click", "attack", "use", "inventory"):
        if getattr(a, flag):
            parts.append(flag)
    if a.hotbar:
        parts.append(f"hotbar {a.hotbar}")
    if a.hold_steps:
        parts.append(f"duration {a.hold_steps / STEPS_PER_SECOND:.2f} s")
    return "; ".join(parts)


@dataclass
class FableAgent:
    workdir: Path
    model: str = MODEL
    history: int = 5
    timeout_s: float = 120.0
    runner: Runner = default_runner
    name: str = "fable-5.1"
    goal: str = ""
    _past: list[str] = field(default_factory=list)
    _last_latency: float | None = None
    _prompt: str = field(default="", init=False)

    def __post_init__(self):
        self.workdir = Path(self.workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._mcp = self.workdir / "empty-mcp.json"
        self._mcp.write_text('{"mcpServers":{}}')
        self._prompt = PROMPT_PATH.read_text()

    @property
    def prompt_version(self) -> str:
        return self._prompt.splitlines()[0].strip()

    def reset(self, goal: str) -> None:
        self.goal = goal
        self._past = []
        self._last_latency = None

    def args(self) -> list[str]:
        return [
            shutil.which("claude") or "claude", "-p",
            "--model", self.model,
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            "--max-turns", "1",
            "--tools", "",
            "--strict-mcp-config", "--mcp-config", str(self._mcp),
            "--setting-sources", "",
            "--system-prompt", self._prompt,
            "--disable-slash-commands",
        ]

    def user_text(self, obs: Observation) -> str:
        lines = [f"Goal: {self.goal}", f"Time elapsed: {obs.game_seconds:.1f} s."]
        if self._last_latency is not None:
            lines.append(f"Your last decision took {self._last_latency:.1f} s to think.")
        if self._past:
            lines.append("Your most recent decisions, oldest first:")
            lines += [f"- {p}" for p in self._past]
        lines.append("Reply with one JSON object.")
        return "\n".join(lines)

    def act(self, obs: Observation) -> tuple[Action, ActMeta]:
        msg = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": png_b64(obs.frame)}},
                    {"type": "text", "text": self.user_text(obs)},
                ],
            },
        }
        t = time.perf_counter()
        code, stdout, stderr = self.runner(self.args(), json.dumps(msg) + "\n", subprocess_env(), self.timeout_s)
        wall = time.perf_counter() - t
        event = None
        for line in stdout.splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "result":
                event = d
        event = classify_result(event, stderr)
        text = event.get("result") or ""
        action, format_error = parse_action(text)
        u = event.get("usage") or {}
        reason = ""
        m = re.search(r'"reason"\s*:\s*"([^"]{0,120})', text)
        if m:
            reason = f" ({m.group(1)})"
        self._past = (self._past + [action_text(action) + reason])[-self.history:]
        meta = ActMeta(
            latency_s=float(event.get("duration_api_ms", wall * 1000)) / 1000,
            wall_s=wall,
            calls=1,
            input_tokens=int(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)),
            output_tokens=int(u.get("output_tokens", 0)),
            raw=text,
            format_error=format_error,
            cost_usd=event.get("total_cost_usd"),
        )
        self._last_latency = meta.latency_s
        return action, meta

    def config(self) -> dict:
        return {"type": "fable", "model": self.model, "history": self.history, "prompt_version": self.prompt_version,
                "timeout_s": self.timeout_s}
