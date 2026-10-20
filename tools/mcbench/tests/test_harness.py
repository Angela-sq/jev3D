import json

import pytest

from fakes import FakeEnv
from mcbench.budget import Budget
from mcbench.harness import RunConfig, run_episode, run_suite
from mcbench.recorder import RunRecorder
from mcbench.tasks import Task, instantiate
from mcbench.types import Action, ActMeta, InfraError, Observation, Status


def task(t=5.0, **kw):
    d = dict(id="kill", category="combat", difficulty=1, goal_text="kill it", time_limit_s=t,
             success=[{"counter": "kill_entity.zombie", "op": ">=", "value": 1}],
             dev_seeds=[1, 2, 3], heldout_seeds=[4, 5], arena=False)
    d.update(kw)
    return Task.from_dict(d)


class SeqAgent:
    """Returns the given actions in order (last one repeats) with a fixed latency."""

    name = "seq"

    def __init__(self, actions, latency=0.0, calls=1, raise_on=None):
        self.actions, self.latency, self.calls, self.raise_on = actions, latency, calls, raise_on
        self.n = 0
        self.seen = []

    def reset(self, goal):
        self.goal = goal

    def act(self, obs):
        self.seen.append(obs)
        self.n += 1
        if self.raise_on == self.n:
            raise InfraError("rate_limit", "usage limit reached", stop_run=True)
        a = self.actions[min(self.n - 1, len(self.actions) - 1)]
        return a, ActMeta(latency_s=self.latency, wall_s=self.latency, calls=self.calls)

    def config(self):
        return {"type": "seq"}


FWD = Action(keys=frozenset({"forward"}))
JUMP = Action(keys=frozenset({"jump"}))


def budget(tmp_path, ep=1000, run=10000):
    return Budget(ep, run, tmp_path / "ledger.json", 10**9)


def run(tmp_path, env, agent, mode, t=None, b=None, spec_task=None):
    spec = instantiate(spec_task or task(t or 5.0), 1, "dev")
    rec = RunRecorder(tmp_path, "r", {}, provenance=False)
    return run_episode(env, agent, spec, mode, b or budget(tmp_path), rec)


def test_paused_holds_new_action_10_steps(tmp_path):
    env = FakeEnv()
    r = run(tmp_path, env, SeqAgent([FWD, JUMP]), "paused", t=1.0)
    assert [a["forward"] for a in env.applied[:10]] == [1] * 10
    assert [a["jump"] for a in env.applied[10:20]] == [1] * 10
    assert r.status == Status.MODEL_FAILURE and r.reason == "time_limit"
    assert r.steps == 20 and r.decisions == 2


def test_charged_applies_previous_action_for_latency_steps(tmp_path):
    env = FakeEnv()
    run(tmp_path, env, SeqAgent([FWD, JUMP], latency=0.25), "charged", t=1.0)
    # decision 1: 5 steps of the previous action (noop); decision 2: 5 steps of FWD; then JUMP.
    assert [a["forward"] for a in env.applied[:5]] == [0] * 5
    assert [a["forward"] for a in env.applied[5:10]] == [1] * 5
    assert [a["jump"] for a in env.applied[10:15]] == [1] * 5


def test_time_limit_is_exact(tmp_path):
    env = FakeEnv()
    r = run(tmp_path, env, SeqAgent([FWD], latency=0.7), "charged", t=1.0)
    assert len(env.applied) == 20 and r.game_seconds == 1.0


def test_success_ends_episode(tmp_path):
    env = FakeEnv(kill_at_step=15)
    r = run(tmp_path, env, SeqAgent([FWD]), "paused", t=10.0)
    assert r.status == Status.SUCCESS and r.steps == 20


def test_budget_cap_gives_truncated(tmp_path):
    env = FakeEnv()
    r = run(tmp_path, env, SeqAgent([FWD]), "paused", t=10.0, b=budget(tmp_path, ep=3))
    assert r.status == Status.BUDGET_TRUNCATED and r.calls == 3 and r.steps == 30


def test_outcome_beats_cap_on_same_step(tmp_path):
    env = FakeEnv(kill_at_step=30)
    r = run(tmp_path, env, SeqAgent([FWD]), "paused", t=10.0, b=budget(tmp_path, ep=3))
    assert r.status == Status.SUCCESS


def test_env_crash_is_infra(tmp_path):
    env = FakeEnv(crash_on_step_call=2)
    r = run(tmp_path, env, SeqAgent([FWD]), "paused", t=10.0)
    assert r.status == Status.INFRA_ERROR and r.reason.startswith("env")


def test_agent_never_sees_info(tmp_path):
    agent = SeqAgent([FWD])
    run(tmp_path, FakeEnv(), agent, "paused", t=1.0)
    for o in agent.seen:
        assert isinstance(o, Observation)
        assert set(vars(o)) == {"frame", "goal", "step", "game_seconds"}


def test_inventory_pressed_once_in_charged_mode(tmp_path):
    env = FakeEnv()
    inv = Action(inventory=True)
    run(tmp_path, env, SeqAgent([inv, Action()], latency=0.1), "charged", t=1.0)
    assert sum(a["inventory"] for a in env.applied) == 1


def cfg(tmp_path, **kw):
    d = dict(run_id="r", runs_dir=str(tmp_path), tasks=["kill"], splits=["dev"], seeds_per_split=None,
             modes=["paused"], max_calls_episode=100, max_calls_run=1000, max_calls_global=10**9,
             confirm_threshold=10**9, agent={"type": "seq"}, ledger=str(tmp_path / "ledger.json"))
    d.update(kw)
    return RunConfig(**d)


def test_run_stops_on_rate_limit(tmp_path):
    tasks = {"kill": task(1.0)}
    agent = SeqAgent([FWD], raise_on=3)
    out = run_suite(cfg(tmp_path), FakeEnv(), agent, tasks)
    statuses = [json.loads(p.read_text())["status"] for p in sorted(out.glob("episodes/kill/*/paused/result.json"))]
    assert statuses == ["model_failure", "infra_error", "not_run"]


def test_resume_skips_finished(tmp_path):
    tasks = {"kill": task(1.0)}
    env = FakeEnv()
    run_suite(cfg(tmp_path), env, SeqAgent([FWD], raise_on=3), tasks)
    env2 = FakeEnv()
    run_suite(cfg(tmp_path), env2, SeqAgent([FWD]), tasks)
    assert [s for s, _ in env2.resets] == [2, 3]
    ledger = json.loads((tmp_path / "ledger.json").read_text())["calls"]
    assert ledger == 2 + 4  # first run: seed 1 (2 calls), then the raising call is not counted


def test_run_cap_marks_rest_not_run(tmp_path):
    tasks = {"kill": task(1.0)}
    out = run_suite(cfg(tmp_path, max_calls_run=2), FakeEnv(), SeqAgent([FWD]), tasks)
    statuses = [json.loads(p.read_text())["status"] for p in sorted(out.glob("episodes/kill/*/paused/result.json"))]
    assert statuses == ["model_failure", "not_run", "not_run"]


def test_episode_ends_at_time_limit_without_time_limit_rule(tmp_path):
    t = task(1.0, failure=[{"dead": True}])
    r = run(tmp_path, FakeEnv(), SeqAgent([FWD]), "paused", spec_task=t)
    assert r.status == Status.MODEL_FAILURE and r.reason == "time_limit" and r.steps == 20


class CmdEnv(FakeEnv):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.commands = []

    def command(self, commands):
        out = super().command(commands)
        if len(self.resets) and self.setup_seen:
            self.commands.append((len(self.applied), list(commands)))
        self.setup_seen = True
        return out

    def reset(self, seed, commands):
        self.setup_seen = False
        return super().reset(seed, commands)


def test_timed_event_fires_at_its_step(tmp_path):
    env = CmdEnv()
    t = task(2.0, events=[{"at_s": 0.75, "commands": ["/time set night"]}])
    run(tmp_path, env, SeqAgent([FWD]), "paused", spec_task=t)
    assert env.commands == [(15, ["/time set night"])]
    assert len(env.applied) == 40


def test_after_reset_commands_run_once_before_play(tmp_path):
    env = CmdEnv()
    spec = instantiate(task(1.0), 1, "dev")
    rec = RunRecorder(tmp_path, "r", {}, provenance=False)
    run_episode(env, SeqAgent([FWD]), spec, "paused", budget(tmp_path), rec, after_reset=["/tp @s ~ ~5 ~"])
    assert env.commands == [(0, ["/tp @s ~ ~5 ~"])]


def test_click_releases_then_presses_each_decision(tmp_path):
    env = FakeEnv()
    hit = Action(click=True)
    run(tmp_path, env, SeqAgent([hit]), "paused", t=1.0)
    attack = [a["attack"] for a in env.applied]
    assert attack[:10] == [0] + [1] * 9
    assert attack[10:20] == [0] + [1] * 9


def test_click_not_repeated_when_carried_over_in_charged_mode(tmp_path):
    env = FakeEnv()
    run(tmp_path, env, SeqAgent([Action(click=True), Action()], latency=0.25), "charged", t=1.0)
    attack = [a["attack"] for a in env.applied]
    # decision 1: noop for 5 steps; decision 2: carried click -> release + press for 5 steps; then no attack.
    assert attack[:5] == [0] * 5
    assert attack[5:10] == [0, 1, 1, 1, 1]
    assert sum(attack[10:]) == 0


def test_camera_turn_applied_on_first_step_only(tmp_path):
    env = FakeEnv()
    run(tmp_path, env, SeqAgent([Action(yaw=30, pitch=-10, keys=frozenset({"forward"}))]), "paused", t=0.5)
    cams = [a["camera"] for a in env.applied]
    assert cams[0] == [-10.0, 30.0]
    assert all(c == [0.0, 0.0] for c in cams[1:10])
    assert all(a["forward"] == 1 for a in env.applied[:10])


def test_camera_turn_not_repeated_when_carried_in_charged_mode(tmp_path):
    env = FakeEnv()
    run(tmp_path, env, SeqAgent([Action(yaw=20), Action()], latency=0.25), "charged", t=1.0)
    turns = [a["camera"][1] for a in env.applied]
    assert turns.count(20.0) == 1 and turns[5] == 20.0


def test_charged_duration_runs_now_then_stands_still(tmp_path):
    env = FakeEnv()
    fwd_short = Action(keys=frozenset({"forward"}), hold_steps=3)
    run(tmp_path, env, SeqAgent([fwd_short, JUMP], latency=0.25), "charged", t=1.0)
    # decision 1: 5 noop steps while thinking, then 3 forward steps right away;
    # decision 2: 5 steps standing still (duration over), then JUMP carries.
    assert [a["forward"] for a in env.applied[:8]] == [0] * 5 + [1] * 3
    assert [a["forward"] + a["jump"] for a in env.applied[8:13]] == [0] * 5
    assert [a["jump"] for a in env.applied[13:18]] == [1] * 5
