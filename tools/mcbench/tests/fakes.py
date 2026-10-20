"""A fake env server for harness tests. Records which env action ran on each step."""

from __future__ import annotations

import numpy as np

from mcbench.envclient import StepOut
from mcbench.harness import SETTLE_STEPS
from mcbench.types import InfraError


class FakeEnv:
    def __init__(self, kill_at_step=None, crash_on_step_call=None, damage_per_step=0.0):
        self.kill_at_step = kill_at_step
        self.crash_on_step_call = crash_on_step_call
        self.damage_per_step = damage_per_step
        self.all_steps = []  # one env action dict per env step, including warm-up
        self.play_from = None
        self.step_calls = 0
        self.resets = []

    @property
    def applied(self):
        """Env actions applied during play (after the chat fade, setup, and settle steps)."""
        return [] if self.play_from is None else self.all_steps[self.play_from:]

    def _info(self):
        steps = len(self.applied)
        kills = 1 if self.kill_at_step is not None and steps >= self.kill_at_step else 0
        return {
            "health": max(0.0, 20.0 - self.damage_per_step * steps),
            "player_pos": {"x": 0.0, "y": 64.0, "z": 0.0},
            "kill_entity": {"zombie": kills} if kills else {},
            "inventory": {},
        }

    def _frame(self):
        return np.zeros((8, 8, 3), dtype=np.uint8)

    def health(self):
        return True

    def reset(self, seed, commands):
        self.resets.append((seed, list(commands)))
        self.all_steps = []
        self.play_from = None
        return StepOut(self._frame(), self._info(), [], False)

    def step(self, env_action, n):
        self.step_calls += 1
        if self.crash_on_step_call == self.step_calls:
            raise InfraError("env", "container died")
        trace = []
        for i in range(n):
            a = dict(env_action)
            if i > 0:
                a["inventory"] = 0
            self.all_steps.append(a)
            info = self._info()
            trace.append({"health": info["health"], "player_pos": info["player_pos"]})
        return StepOut(self._frame(), self._info(), trace, False)

    def command(self, commands):
        if self.play_from is None:
            self.play_from = len(self.all_steps) + SETTLE_STEPS
        return StepOut(self._frame(), self._info(), [], False)
