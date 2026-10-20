"""Converts mcbench Actions into MineStudio's env action format."""

from __future__ import annotations

from mcbench.types import KEYS, Action

MAX_TURN = 30.0
BUTTONS = ("attack", "use", "inventory", "drop", "swapHands", "pickItem", "ESC")
ENV_KEYS = KEYS + BUTTONS + tuple(f"hotbar.{i}" for i in range(1, 10)) + ("camera",)


def clamp(x: float) -> float:
    return max(-MAX_TURN, min(MAX_TURN, float(x)))


def to_env_action(a: Action) -> dict:
    env = {k: 0 for k in ENV_KEYS}
    for k in a.keys:
        if k in KEYS:
            env[k] = 1
    env["attack"] = int(a.attack)
    env["use"] = int(a.use)
    env["inventory"] = int(a.inventory)
    if a.hotbar is not None and 1 <= a.hotbar <= 9:
        env[f"hotbar.{a.hotbar}"] = 1
    env["camera"] = [clamp(a.pitch), clamp(a.yaw)]
    return env
