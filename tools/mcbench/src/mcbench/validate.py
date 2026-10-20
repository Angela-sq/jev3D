"""Checks each task's rules fire correctly, with no model calls.

Per task, on its first dev seed:
  1. noop: a NoopAgent plays for up to 10 game seconds. It must not succeed
     (survival tasks: it must not fail early either).
  2. oracle: the task's oracle commands force the success condition once the start
     position is recorded (plus any oracle events), then a ScriptedAgent holds the
     oracle's action. It must succeed.
"""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

from mcbench.agents.simple import NoopAgent, ScriptedAgent
from mcbench.budget import Budget
from mcbench.harness import run_episode
from mcbench.recorder import RunRecorder
from mcbench.tasks import Task, fill, instantiate
from mcbench.types import Action, Status

NOOP_SECONDS = 10.0


def oracle_action(hold: dict) -> Action:
    return Action(
        keys=frozenset(hold.get("keys", [])),
        attack=bool(hold.get("attack", False)),
        click=bool(hold.get("click", False)),
        use=bool(hold.get("use", False)),
    )


def validate_task(env, t: Task, rec: RunRecorder) -> dict:
    budget = Budget(10**6, 10**6, rec.dir / "ledger.json", 10**9)
    seed = t.dev_seeds[0]

    spec = instantiate(t, seed, "dev")
    spec = dataclasses.replace(spec, time_limit_s=min(NOOP_SECONDS, spec.time_limit_s))
    noop = run_episode(env, NoopAgent(), spec, "paused", budget, rec)
    survival = any("survive_s" in r for r in spec.success)
    noop_ok = noop.status == Status.MODEL_FAILURE and (not survival or noop.reason == "time_limit")

    spec = instantiate(t, seed, "dev")
    oracle = t.oracle or {}
    steps = int(oracle.get("steps", 20))
    spec = dataclasses.replace(
        spec,
        events=sorted(spec.events + fill(list(oracle.get("events", [])), spec.values), key=lambda e: e["at_s"]),
        time_limit_s=spec.time_limit_s if survival else steps / 20,
    )
    agent = ScriptedAgent(oracle_action(oracle.get("hold", {})), name="oracle")
    after = fill(list(oracle.get("commands", [])), spec.values)
    orc = run_episode(env, agent, spec, "paused", budget, rec, after_reset=after or None)
    return {
        "task": t.id,
        "seed": seed,
        "noop_status": f"{noop.status.value} ({noop.reason})",
        "noop_ok": noop_ok,
        "oracle_status": f"{orc.status.value} ({orc.reason})",
        "oracle_ok": orc.status == Status.SUCCESS,
    }


def validate(env, tasks: dict[str, Task], ids: list[str], runs_dir: Path, out_md: Path) -> list[dict]:
    rec = RunRecorder(runs_dir, f"validate-{int(time.time())}", {"tasks": ids})
    rows = []
    for tid in ids:
        row = validate_task(env, tasks[tid], rec)
        rows.append(row)
        print(row, flush=True)
    lines = [
        "| task | seed | noop | noop ok | oracle | oracle ok |",
        "|---|---|---|---|---|---|",
    ] + [
        f"| {r['task']} | {r['seed']} | {r['noop_status']} | {r['noop_ok']} | {r['oracle_status']} | {r['oracle_ok']} |"
        for r in rows
    ]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "a") as f:
        f.write(f"\n## Validation run {rec.dir.name}\n\n" + "\n".join(lines) + "\n")
    return rows
