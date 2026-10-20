"""Plug for local policies, such as a future Jev-trained student.

The policy is any function (frame, goal) -> Action. Latency is the wall time of the
call on this machine; the harness charges it in charged mode like any other agent.
A policy that wants per-step control returns Action(hold_steps=1); one that keeps a
frame history stores it itself between calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from mcbench.types import Action, ActMeta, Observation


@dataclass
class PolicyStubAgent:
    fn: Callable[[np.ndarray, str], Action]
    name: str = "policy"
    goal: str = ""

    def reset(self, goal: str) -> None:
        self.goal = goal

    def act(self, obs: Observation) -> tuple[Action, ActMeta]:
        t = time.perf_counter()
        a = self.fn(obs.frame, obs.goal)
        wall = time.perf_counter() - t
        return a, ActMeta(latency_s=wall, wall_s=wall)

    def config(self) -> dict:
        return {"type": "policy", "fn": getattr(self.fn, "__name__", repr(self.fn))}
