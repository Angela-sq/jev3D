"""Shared data types for mcbench. Agents see Observation only, never game info."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

KEYS = ("forward", "back", "left", "right", "jump", "sneak", "sprint")


@dataclass(frozen=True)
class Action:
    """One decision. Camera turn is in degrees; yaw > 0 turns right, pitch > 0 looks down."""

    keys: frozenset[str] = frozenset()
    yaw: float = 0.0
    pitch: float = 0.0
    attack: bool = False  # hold left mouse (breaking blocks needs it held)
    click: bool = False  # one fresh left click at the start of this action (hitting mobs)
    use: bool = False
    hotbar: int | None = None
    inventory: bool = False
    hold_steps: int | None = None

    @staticmethod
    def noop() -> Action:
        return Action()


@dataclass(frozen=True)
class Observation:
    frame: np.ndarray
    goal: str
    step: int
    game_seconds: float


@dataclass(frozen=True)
class ActMeta:
    latency_s: float
    wall_s: float
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: str = ""
    format_error: bool = False
    cost_usd: float | None = None  # API-equivalent estimate, not billed


class Status(str, Enum):
    SUCCESS = "success"
    MODEL_FAILURE = "model_failure"
    BUDGET_TRUNCATED = "budget_truncated"
    INFRA_ERROR = "infra_error"
    NOT_RUN = "not_run"


SCORED = (Status.SUCCESS, Status.MODEL_FAILURE)


class InfraError(Exception):
    """A failure of the harness, env, or model service rather than the model's play."""

    def __init__(self, kind: str, message: str, stop_run: bool = False):
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.stop_run = stop_run


@dataclass
class EpisodeResult:
    task: str
    category: str
    difficulty: int
    seed: int
    split: str
    mode: str
    agent: str
    status: Status
    reason: str = ""
    steps: int = 0
    game_seconds: float = 0.0
    decisions: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    format_errors: int = 0
    latency_mean_s: float = 0.0
    latency_p90_s: float = 0.0
    wall_latency_mean_s: float = 0.0
    final_health: float = 0.0
    damage_taken: float = 0.0
    damage_dealt: float = 0.0
    deaths: int = 0
    collisions: int = 0
    cost_usd_api_equiv: float = 0.0
    extra: dict = field(default_factory=dict)
