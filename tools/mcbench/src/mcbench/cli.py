"""mcbench command line.

  mcbench smoke                      small Fable run (configs/smoke.yaml)
  mcbench run <config> [--yes]       run a config; asks for --yes above its call threshold
  mcbench estimate <config>          print the planned number of model calls
  mcbench validate [task ...]        check task rules with no model calls
  mcbench analyze <run_dir>          tables and plots for a run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from mcbench.budget import estimate_calls
from mcbench.envclient import EnvClient
from mcbench.harness import RunConfig, episode_list, run_suite
from mcbench.tasks import load_tasks

SMOKE = Path("configs/smoke.yaml")


def make_agent(spec: dict, run_dir: Path):
    kind = spec.get("type")
    if kind == "fable":
        from mcbench.agents.fable import FableAgent, check_auth

        check_auth()
        return FableAgent(workdir=run_dir / "claude-workdir", history=spec.get("history", 5))
    if kind == "random":
        from mcbench.agents.simple import RandomAgent

        return RandomAgent(seed=spec.get("seed", 0))
    if kind == "noop":
        from mcbench.agents.simple import NoopAgent

        return NoopAgent()
    raise SystemExit(f"unknown agent type {kind!r}")


def planned(cfg: RunConfig, tasks) -> int:
    if cfg.agent.get("type") != "fable":
        return 0
    eps = episode_list(cfg, tasks)
    per_task = {}
    for t, _, _, mode in eps:
        per_task.setdefault((t.id, mode), [t, 0])[1] += 1
    total = 0
    for (tid, mode), (t, n) in per_task.items():
        total += min(estimate_calls([t], n, [mode]), n * cfg.max_calls_episode)
    return min(total, cfg.max_calls_run)


def cmd_run(cfg_path: Path, yes: bool, agent: str | None) -> None:
    cfg = RunConfig.load(cfg_path)
    if agent:
        cfg.agent = {"type": agent}
        cfg.run_id = f"{cfg.run_id}-{agent}"
    if "{time}" in cfg.run_id:
        cfg.run_id = cfg.run_id.replace("{time}", time.strftime("%Y%m%d-%H%M%S"))
    tasks = load_tasks()
    n = planned(cfg, tasks)
    print(f"{len(episode_list(cfg, tasks))} episodes, up to {n} model calls (caps: episode {cfg.max_calls_episode}, run {cfg.max_calls_run})")
    if n > cfg.confirm_threshold and not yes:
        raise SystemExit(f"Planned calls {n} > confirm_threshold {cfg.confirm_threshold}. Re-run with --yes to start.")
    env = EnvClient(cfg.env_url)
    if not env.health():
        raise SystemExit("env server not healthy; start it with docker/run.sh")
    run_dir = Path(cfg.runs_dir) / cfg.run_id
    out = run_suite(cfg, env, make_agent(cfg.agent, run_dir), tasks)
    print(f"run folder: {out}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="mcbench")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("smoke")
    s.add_argument("--agent")
    r = sub.add_parser("run")
    r.add_argument("config", type=Path)
    r.add_argument("--yes", action="store_true")
    r.add_argument("--agent", help="override agent type (fable, random, noop)")
    e = sub.add_parser("estimate")
    e.add_argument("config", type=Path)
    v = sub.add_parser("validate")
    v.add_argument("tasks", nargs="*")
    a = sub.add_parser("analyze")
    a.add_argument("run_dir", type=Path)
    args = p.parse_args(argv)

    if args.cmd == "smoke":
        cmd_run(SMOKE, False, args.agent)
    elif args.cmd == "run":
        cmd_run(args.config, args.yes, args.agent)
    elif args.cmd == "estimate":
        cfg = RunConfig.load(args.config)
        tasks = load_tasks()
        print(f"{len(episode_list(cfg, tasks))} episodes, up to {planned(cfg, tasks)} model calls")
    elif args.cmd == "validate":
        from mcbench.validate import validate

        tasks = load_tasks()
        ids = args.tasks or list(tasks)
        rows = validate(EnvClient(), tasks, ids, Path("runs"), Path("docs/validation.md"))
        bad = [r["task"] for r in rows if not (r["noop_ok"] and r["oracle_ok"])]
        print("ALL VALID" if not bad else f"NOT VALID: {bad}")
        sys.exit(1 if bad else 0)
    elif args.cmd == "analyze":
        from mcbench.analysis import analyze

        analyze(args.run_dir)


if __name__ == "__main__":
    main()
