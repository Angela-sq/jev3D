"""Baseline agents that make no model calls."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from mcbench.types import KEYS, Action, ActMeta, Observation


@dataclass
class NoopAgent:
    name: str = "noop"

    def reset(self, goal: str) -> None:
        pass

    def act(self, obs: Observation) -> tuple[Action, ActMeta]:
        return Action.noop(), ActMeta(latency_s=0.0, wall_s=0.0)

    def config(self) -> dict:
        return {"type": "noop"}


@dataclass
class RandomAgent:
    seed: int = 0
    name: str = "random"
    rng: np.random.Generator = field(init=False)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)

    def reset(self, goal: str) -> None:
        pass

    def act(self, obs: Observation) -> tuple[Action, ActMeta]:
        t = time.perf_counter()
        keys = frozenset(k for k in KEYS if self.rng.random() < 0.2)
        a = Action(
            keys=keys,
            yaw=float(self.rng.uniform(-30, 30)),
            pitch=float(self.rng.uniform(-10, 10)),
            attack=bool(self.rng.random() < 0.3),
            use=bool(self.rng.random() < 0.1),
        )
        wall = time.perf_counter() - t
        return a, ActMeta(latency_s=wall, wall_s=wall)

    def config(self) -> dict:
        return {"type": "random", "seed": self.seed}


@dataclass
class ScriptedAgent:
    """Repeats one fixed action. Used by task validation oracles."""

    action: Action
    name: str = "scripted"

    def reset(self, goal: str) -> None:
        pass

    def act(self, obs: Observation) -> tuple[Action, ActMeta]:
        return self.action, ActMeta(latency_s=0.0, wall_s=0.0)

    def config(self) -> dict:
        return {"type": "scripted", "action": repr(self.action)}
