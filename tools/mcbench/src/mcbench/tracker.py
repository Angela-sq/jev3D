"""Accumulates per-step metrics during an episode and decides when it ends."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from mcbench.tasks import EpisodeSpec, RuleState, rule_holds, rule_name
from mcbench.timing import STEPS_PER_SECOND
from mcbench.types import Status

COLLISION_WINDOW = 4
COLLISION_MIN_MOVE = 0.05
RESPAWN_JUMP = 4.0


def pos_of(info: dict) -> tuple[float, float, float]:
    p = info.get("player_pos") or {}
    return float(p.get("x", 0.0)), float(p.get("y", 0.0)), float(p.get("z", 0.0))


@dataclass
class Tracker:
    spec: EpisodeSpec
    spawn: tuple[float, float, float]
    health: float = 20.0
    min_health: float = 20.0
    steps: int = 0
    damage_taken: float = 0.0
    deaths: int = 0
    collisions: int = 0
    info: dict = field(default_factory=dict)
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    _window: list = field(default_factory=list)
    positions: list = field(default_factory=list)

    def __post_init__(self):
        self.pos = self.spawn

    @property
    def game_seconds(self) -> float:
        return self.steps / STEPS_PER_SECOND

    def update(self, trace: list[dict], keys: frozenset[str], info: dict | None = None) -> None:
        """Add one chunk of env steps, all taken with the same held keys."""
        for t in trace:
            self.steps += 1
            before = self.pos
            h = t.get("health")
            if h is not None:
                h = float(h)
                if h < self.health:
                    self.damage_taken += self.health - h
                # MineStudio never reports health 0: on death it jumps from the last
                # damaged value straight to 20 on respawn. Natural regen is far slower.
                if (h <= 0 < self.health) or (h >= 19.5 and h - self.health > RESPAWN_JUMP):
                    self.deaths += 1
                self.health = h
                self.min_health = min(self.min_health, h)
            if t.get("player_pos"):
                self.pos = pos_of(t)
                self.positions.append(self.pos)
            self._collision_step("forward" in keys, before)
        if info is not None:
            self.info = info

    def _collision_step(self, forward: bool, before: tuple[float, float, float]) -> None:
        if not forward:
            self._window.clear()
            return
        if not self._window:
            self._window.append(before)
        self._window.append(self.pos)
        if len(self._window) == COLLISION_WINDOW + 1:
            (x0, _, z0), (x1, _, z1) = self._window[0], self._window[-1]
            if math.hypot(x1 - x0, z1 - z0) < COLLISION_MIN_MOVE:
                self.collisions += 1
            self._window = [self._window[-1]]

    @property
    def dead(self) -> bool:
        return self.deaths > 0

    def damage_dealt(self) -> float:
        d = self.info.get("damage_dealt") or {}
        return float(sum(v for v in d.values() if isinstance(v, (int, float)))) if isinstance(d, dict) else 0.0

    def check(self) -> tuple[Status | None, str]:
        s = RuleState(self.info, self.spawn, self.pos, self.game_seconds, self.spec.time_limit_s, self.dead,
                      self.positions)
        if all(rule_holds(r, s) for r in self.spec.success):
            return Status.SUCCESS, "success"
        for r in self.spec.failure:
            if rule_holds(r, s):
                return Status.MODEL_FAILURE, rule_name(r)
        return None, ""
