"""Episode loop and suite runner."""

from __future__ import annotations

import dataclasses
import traceback
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import yaml

from mcbench.actions import to_env_action
from mcbench.budget import Budget
from mcbench.recorder import RunRecorder
from mcbench.tasks import BASE_COMMANDS, EpisodeSpec, Task, instantiate
from mcbench.timing import STEPS_PER_SECOND, steps_for
from mcbench.tracker import Tracker, pos_of
from mcbench.types import Action, InfraError, Observation, Status, EpisodeResult


# Chat lines stay on screen for 10 s. After BASE_COMMANDS the harness idles this long
# so nothing printed before sendCommandFeedback took effect is still visible.
CHAT_FADE_STEPS = 220
# Steps after the task setup so the first frame shows the finished setup.
SETTLE_STEPS = 5


@dataclass
class RunConfig:
    run_id: str
    tasks: list[str] | str = "all"
    splits: list[str] = field(default_factory=lambda: ["dev", "heldout"])
    seeds_per_split: int | None = None  # None = all seeds the task lists
    modes: list[str] = field(default_factory=lambda: ["charged", "paused"])
    max_calls_episode: int = 400
    max_calls_run: int = 17000
    max_calls_global: int = 40000
    confirm_threshold: int = 500
    agent: dict = field(default_factory=lambda: {"type": "fable"})
    runs_dir: str = "runs"
    ledger: str = "runs/ledger.json"
    env_url: str = "http://127.0.0.1:8765"
    include_unvalidated: bool = False

    @staticmethod
    def load(path: Path, **overrides) -> RunConfig:
        d = yaml.safe_load(Path(path).read_text())
        d.update({k: v for k, v in overrides.items() if v is not None})
        return RunConfig(**d)


def episode_list(cfg: RunConfig, tasks: dict[str, Task]) -> list[tuple[Task, int, str, str]]:
    ids = list(tasks) if cfg.tasks == "all" else list(cfg.tasks)
    out = []
    for tid in ids:
        t = tasks[tid]
        if not t.validated and not cfg.include_unvalidated and cfg.tasks == "all":
            continue
        for split in cfg.splits:
            seeds = t.dev_seeds if split == "dev" else t.heldout_seeds
            if cfg.seeds_per_split is not None:
                seeds = seeds[: cfg.seeds_per_split]
            for seed in seeds:
                for mode in cfg.modes:
                    out.append((t, seed, split, mode))
    return out


def run_episode(env, agent, spec: EpisodeSpec, mode: str, budget: Budget, rec: RunRecorder,
                after_reset: list[str] | None = None) -> EpisodeResult:
    """Play one episode. after_reset commands run once the start position is recorded
    (validation oracles only). Timed spec.events run when game time reaches them."""
    task = spec.task
    ep = rec.episode(task.id, spec.seed, mode)
    res = EpisodeResult(task.id, task.category, task.difficulty, spec.seed, spec.split, mode,
                        getattr(agent, "name", "agent"), Status.INFRA_ERROR)
    latencies, walls = [], []
    tracker = None
    budget.start_episode()
    stop_error = None
    limit_steps = round(spec.time_limit_s * STEPS_PER_SECOND)

    try:
        noop = to_env_action(Action.noop())
        env.reset(spec.seed, BASE_COMMANDS)
        env.step(noop, CHAT_FADE_STEPS)
        env.command(spec.commands)
        out = env.step(noop, SETTLE_STEPS)
        tracker = Tracker(spec, pos_of(out.info))
        tracker.update([], frozenset(), out.info)
        frame = out.frame
        if after_reset:
            out = env.command(after_reset)
            tracker.update(out.trace, frozenset(), out.info)
            frame = out.frame
        events = list(spec.events)
        agent.reset(spec.goal_text)
        prev = Action.noop()

        def run(a: Action, n: int) -> Action:
            """Step the env n times with a, firing timed events on time. Returns a with
            the inventory press used up (the key toggles, so it is pressed once)."""
            nonlocal frame
            while n > 0:
                m = n
                if events:
                    due = round(events[0]["at_s"] * STEPS_PER_SECOND) - tracker.steps
                    if due <= 0:
                        o = env.command(events.pop(0)["commands"])
                        tracker.update([], a.keys, o.info)
                        continue
                    m = min(n, due)
                o = env.step(to_env_action(a), m)
                tracker.update(o.trace, a.keys, o.info)
                ep.steps(o.trace, a)
                frame = o.frame
                res.steps = tracker.steps
                n -= m
                if a.inventory:
                    a = replace(a, inventory=False)
                if tracker.check()[0] is not None:
                    break
            return a

        def chunk(a: Action, n: int) -> Action:
            """Apply action a for up to n steps (capped at the time limit).

            One-shot parts happen on the first step only: the camera turn (otherwise a
            30 degree turn held for 10 steps would turn 300 degrees), the inventory key,
            and the release half of a click (Minecraft hits a mob only on a fresh press).
            Returns the action as it should carry over, with the one-shot parts used up.
            """
            n = min(n, limit_steps - tracker.steps)
            carry = replace(a, yaw=0.0, pitch=0.0, click=False, inventory=False)
            if n <= 0:
                return a
            if not (a.yaw or a.pitch or a.click or a.inventory):
                return run(a, n)
            run(replace(a, click=False, attack=a.attack and not a.click), 1)
            if n > 1 and tracker.check()[0] is None:
                run(replace(carry, attack=a.attack or a.click), n - 1)
            return carry

        def outcome():
            st, why = tracker.check()
            if st is None and tracker.steps >= limit_steps:
                st, why = Status.MODEL_FAILURE, "time_limit"
            return st, why

        status, reason = outcome()
        while status is None:
            if not budget.can_call():
                status, reason = Status.BUDGET_TRUNCATED, ("run_cap" if budget.run_exhausted else "episode_cap")
                break
            obs = Observation(frame=frame, goal=spec.goal_text, step=tracker.steps, game_seconds=tracker.game_seconds)
            action, meta = agent.act(obs)
            if meta.calls:
                budget.record_call(meta.calls)
            res.calls += meta.calls
            res.input_tokens += meta.input_tokens
            res.output_tokens += meta.output_tokens
            res.format_errors += int(meta.format_error)
            res.cost_usd_api_equiv += meta.cost_usd or 0.0
            latencies.append(meta.latency_s)
            walls.append(meta.wall_s)
            n_prev, n_new = steps_for(mode, meta.latency_s, action.hold_steps)
            ep.decision(res.decisions, obs.frame, spec.goal_text, action, meta, n_prev, n_new)
            res.decisions += 1

            if n_prev:
                prev = chunk(prev, n_prev)
                status, reason = outcome()
                if status is not None:
                    break
            if n_new:
                # An action with a set duration ends there: the player stands still
                # (all keys and buttons released) until the next action starts.
                chunk(action, n_new)
                prev = Action.noop()
                status, reason = outcome()
            else:
                prev = action
    except InfraError as e:
        status, reason = Status.INFRA_ERROR, f"{e.kind}: {e}"[:500]
        if e.stop_run:
            stop_error = e
    except Exception:
        status, reason = Status.INFRA_ERROR, f"harness: {traceback.format_exc()[-500:]}"

    res.status, res.reason = status, reason
    if tracker is not None:
        res.steps = tracker.steps
        res.game_seconds = tracker.game_seconds
        res.final_health = tracker.health
        res.damage_taken = tracker.damage_taken
        res.damage_dealt = tracker.damage_dealt()
        res.deaths = tracker.deaths
        res.collisions = tracker.collisions
    if latencies:
        res.latency_mean_s = float(np.mean(latencies))
        res.latency_p90_s = float(np.percentile(latencies, 90))
        res.wall_latency_mean_s = float(np.mean(walls))
    res.extra = {"values": spec.values, "goal_text": spec.goal_text}
    ep.finish(res)
    if stop_error is not None:
        raise stop_error
    return res


def not_run(rec: RunRecorder, t: Task, seed: int, split: str, mode: str, agent_name: str, why: str) -> None:
    res = EpisodeResult(t.id, t.category, t.difficulty, seed, split, mode, agent_name, Status.NOT_RUN, why)
    rec.episode(t.id, seed, mode).finish(res)


def run_suite(cfg: RunConfig, env, agent, tasks: dict[str, Task]) -> Path:
    rec = RunRecorder(Path(cfg.runs_dir), cfg.run_id, dataclasses.asdict(cfg) | {"agent_config": agent.config()})
    budget = Budget(cfg.max_calls_episode, cfg.max_calls_run, Path(cfg.ledger), cfg.max_calls_global)
    todo = episode_list(cfg, tasks)
    name = getattr(agent, "name", "agent")
    stopped = ""
    for t, seed, split, mode in todo:
        done = rec.finished_status(t.id, seed, mode)
        if done is not None and done not in (Status.INFRA_ERROR, Status.NOT_RUN):
            continue
        if stopped or budget.run_exhausted:
            not_run(rec, t, seed, split, mode, name, stopped or "budget exhausted")
            continue
        try:
            run_episode(env, agent, instantiate(t, seed, split), mode, budget, rec)
        except InfraError as e:
            stopped = f"run stopped: {e.kind}"
    return rec.dir
