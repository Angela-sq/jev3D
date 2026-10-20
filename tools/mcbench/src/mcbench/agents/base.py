"""The interface every model plays through."""

from __future__ import annotations

from typing import Protocol

from mcbench.types import Action, ActMeta, Observation


class Agent(Protocol):
    name: str

    def reset(self, goal: str) -> None: ...

    def act(self, obs: Observation) -> tuple[Action, ActMeta]: ...

    def config(self) -> dict: ...
