from mcbench.budget import Budget, estimate_calls
from mcbench.tasks import Task


def task(t=60.0):
    return Task.from_dict(dict(
        id="x", category="combat", difficulty=1, goal_text="g", time_limit_s=t,
        success=[{"dead": True}], dev_seeds=[1, 2, 3], heldout_seeds=[4, 5],
    ))


def test_episode_cap(tmp_path):
    b = Budget(2, 100, tmp_path / "ledger.json", 1000)
    b.start_episode()
    assert b.can_call()
    b.record_call()
    b.record_call()
    assert not b.can_call()
    b.start_episode()
    assert b.can_call()


def test_run_cap(tmp_path):
    b = Budget(10, 3, tmp_path / "ledger.json", 1000)
    b.start_episode()
    for _ in range(3):
        b.record_call()
    assert not b.can_call() and b.run_exhausted


def test_global_cap_and_ledger_persists_across_instances(tmp_path):
    p = tmp_path / "ledger.json"
    b = Budget(10, 10, p, 5)
    b.start_episode()
    for _ in range(4):
        b.record_call()
    b2 = Budget(10, 10, p, 5)
    assert b2.global_used == 4
    b2.start_episode()
    b2.record_call()
    assert not b2.can_call() and b2.run_exhausted


def test_estimate_matches_spec_example():
    assert estimate_calls([task(60)], 1, ["paused", "charged"]) == 120 + 47
    assert estimate_calls([task(60)], 5, ["paused"]) == 600
