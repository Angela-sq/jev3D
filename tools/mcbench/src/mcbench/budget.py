"""Model-call limits per episode, per run, and across runs (a ledger file)."""

from __future__ import annotations

import fcntl
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from mcbench.timing import PAUSED_HOLD_STEPS, STEPS_PER_SECOND

DEFAULT_LEDGER = Path("runs") / "ledger.json"


@dataclass
class Budget:
    max_calls_episode: int
    max_calls_run: int
    ledger_path: Path
    max_calls_global: int
    episode_calls: int = 0
    run_calls: int = 0
    _global: int = field(default=0, init=False)

    def __post_init__(self):
        self.ledger_path = Path(self.ledger_path)
        self._global = self._read()

    def _read(self) -> int:
        try:
            return int(json.loads(self.ledger_path.read_text()).get("calls", 0))
        except (FileNotFoundError, ValueError):
            return 0

    def start_episode(self) -> None:
        self.episode_calls = 0

    @property
    def global_used(self) -> int:
        return self._global

    @property
    def run_exhausted(self) -> bool:
        return self.run_calls >= self.max_calls_run or self._global >= self.max_calls_global

    def can_call(self) -> bool:
        return self.episode_calls < self.max_calls_episode and not self.run_exhausted

    def record_call(self, n: int = 1) -> None:
        self.episode_calls += n
        self.run_calls += n
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.ledger_path.with_suffix(".lock")
        with open(lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            total = self._read() + n
            tmp = self.ledger_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"calls": total}))
            os.replace(tmp, self.ledger_path)
        self._global = total


def estimate_calls(tasks, seeds_per_task: int, modes: list[str], latency_s: float = 1.3) -> int:
    """Upper-bound call estimate if every episode runs to its time limit."""
    hold_s = PAUSED_HOLD_STEPS / STEPS_PER_SECOND
    total = 0
    for t in tasks:
        for m in modes:
            per = math.ceil(t.time_limit_s / hold_s) if m == "paused" else math.ceil(t.time_limit_s / latency_s)
            total += per * seeds_per_task
    return total
