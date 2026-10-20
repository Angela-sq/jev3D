"""Charged and paused timing modes."""

from __future__ import annotations

import math

STEPS_PER_SECOND = 20
PAUSED_HOLD_STEPS = 10  # 0.5 s


def steps_for(mode: str, latency_s: float, hold_steps: int | None) -> tuple[int, int]:
    """Return (steps run with the previous action, steps run with the new action).

    Charged: the game runs ceil(latency * 20) steps (at least 1) with the previous
    action while the model thinks. The new action then runs hold_steps steps and
    the player stands still after that; with no hold_steps it runs 0 steps now and
    becomes the previous action for the next decision.
    Paused: the game waits for the model, then runs the new action for hold_steps
    steps (10 by default).
    """
    if mode == "charged":
        return max(1, math.ceil(latency_s * STEPS_PER_SECOND)), hold_steps or 0
    if mode == "paused":
        return 0, hold_steps or PAUSED_HOLD_STEPS
    raise ValueError(f"unknown mode {mode!r}")
