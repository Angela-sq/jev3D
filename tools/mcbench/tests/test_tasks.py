import pytest

from mcbench.tasks import BASE_COMMANDS, Task, instantiate, inventory_count, load_tasks
from mcbench.tracker import Tracker
from mcbench.types import Status


def make_task(**kw):
    d = dict(
        id="t", category="combat", difficulty=1, goal_text="go {dx}", time_limit_s=10,
        setup_commands=["/summon zombie ~{dx} ~ ~{dz}"],
        success=[{"counter": "kill_entity.zombie", "op": ">=", "value": 1}],
        dev_seeds=[1], heldout_seeds=[2],
        params={"dx": {"int": [-5, 5]}, "dz": {"int": [3, 9]}},
    )
    d.update(kw)
    return Task.from_dict(d)


def tracker_for(spec, spawn=(0.0, 64.0, 0.0)):
    return Tracker(spec, spawn)


def info_trace(n, health=20.0, pos=(0.0, 64.0, 0.0)):
    return [{"health": health, "player_pos": {"x": pos[0], "y": pos[1], "z": pos[2]}}] * n


def test_render_commands_deterministic_per_seed():
    t = make_task()
    a, b, c = instantiate(t, 7, "dev"), instantiate(t, 7, "dev"), instantiate(t, 8, "dev")
    assert a.commands == b.commands
    assert a.values != c.values or a.commands == c.commands
    assert not set(BASE_COMMANDS) & set(a.commands)
    assert BASE_COMMANDS[0] == "/gamerule sendCommandFeedback false"
    assert a.goal_text == f"go {a.values['dx']}"


def test_heldout_variant_applied():
    t = make_task(heldout_variant={"setup_commands": ["/summon husk ~{dx} ~ ~{dz}"]})
    assert any("husk" in c for c in instantiate(t, 1, "heldout").commands)
    assert not any("husk" in c for c in instantiate(t, 1, "dev").commands)


def test_counter_rule():
    tr = tracker_for(instantiate(make_task(), 1, "dev"))
    tr.update(info_trace(1), frozenset(), {"kill_entity": {}})
    assert tr.check() == (None, "")
    tr.update(info_trace(1), frozenset(), {"kill_entity": {"zombie": 1}})
    assert tr.check() == (Status.SUCCESS, "success")


def test_inventory_rule_sums_matching_items():
    info = {"inventory": {"0": {"type": "oak_log", "quantity": 3}, "1": {"type": "birch_log", "quantity": 2},
                          "2": {"type": "none", "quantity": 0}}}
    assert inventory_count(info, "log") == 5
    t = make_task(success=[{"inventory": "log", "op": ">=", "value": 5}])
    tr = tracker_for(instantiate(t, 1, "dev"))
    tr.update(info_trace(1), frozenset(), info)
    assert tr.check()[0] == Status.SUCCESS


def test_near_rule_relative_to_spawn():
    t = make_task(success=[{"near": ["{dx}", 0, "{dz}"], "radius": 2.5}])
    spec = instantiate(t, 3, "dev")
    dx, dz = spec.values["dx"], spec.values["dz"]
    tr = tracker_for(spec, spawn=(100.0, 64.0, 200.0))
    tr.update(info_trace(1, pos=(100.0, 64.0, 200.0)), frozenset(), {})
    assert tr.check()[0] is None
    tr.update(info_trace(1, pos=(100.0 + dx + 1, 64.0, 200.0 + dz)), frozenset(), {})
    assert tr.check()[0] == Status.SUCCESS


def test_dead_beats_time_limit():
    tr = tracker_for(instantiate(make_task(time_limit_s=0.1), 1, "dev"))
    tr.update(info_trace(5, health=0.0), frozenset(), {})
    assert tr.check() == (Status.MODEL_FAILURE, "dead")


def test_time_limit_failure():
    tr = tracker_for(instantiate(make_task(time_limit_s=0.5), 1, "dev"))
    tr.update(info_trace(10), frozenset(), {})
    assert tr.check() == (Status.MODEL_FAILURE, "time_limit")


def test_survive_rule():
    t = make_task(success=[{"survive_s": 1}], failure=[{"dead": True}])
    tr = tracker_for(instantiate(t, 1, "dev"))
    tr.update(info_trace(19), frozenset(), {})
    assert tr.check()[0] is None
    tr.update(info_trace(1), frozenset(), {})
    assert tr.check()[0] == Status.SUCCESS


def test_damage_taken_from_health_drops():
    tr = tracker_for(instantiate(make_task(), 1, "dev"))
    trace = [{"health": h} for h in (20, 17, 20, 15)]
    tr.update(trace, frozenset(), {})
    assert tr.damage_taken == 8
    assert tr.min_health == 15


def test_collision_count():
    tr = tracker_for(instantiate(make_task(), 1, "dev"))
    tr.update(info_trace(8), frozenset({"forward"}), {})
    assert tr.collisions == 2
    moving = [{"health": 20, "player_pos": {"x": 0, "y": 64, "z": i * 0.2}} for i in range(8)]
    tr2 = tracker_for(instantiate(make_task(), 1, "dev"))
    tr2.update(moving, frozenset({"forward"}), {})
    assert tr2.collisions == 0
    tr3 = tracker_for(instantiate(make_task(), 1, "dev"))
    tr3.update(info_trace(8), frozenset(), {})
    assert tr3.collisions == 0


@pytest.mark.parametrize("split", ["dev", "heldout"])
def test_all_task_yamls_load_and_instantiate(split):
    tasks = load_tasks()
    assert {"collect_wood", "combat_zombie", "navigate_landmark", "craft_table", "survive_mobs"} <= set(tasks)
    for t in tasks.values():
        assert len(t.dev_seeds) == 3 and len(t.heldout_seeds) == 2
        spec = instantiate(t, (t.dev_seeds if split == "dev" else t.heldout_seeds)[0], split)
        assert all("{" not in c for c in spec.commands), spec.commands
        for rule in spec.success + spec.failure:
            for v in rule.values():
                assert not (isinstance(v, str) and "{" in v), rule
                assert not (isinstance(v, list) and any(isinstance(x, str) for x in v)), rule


def test_rise_rule():
    t = make_task(success=[{"rise": 3}])
    tr = tracker_for(instantiate(t, 1, "dev"), spawn=(0.0, 64.0, 0.0))
    tr.update(info_trace(1, pos=(0.0, 66.0, 0.0)), frozenset(), {})
    assert tr.check()[0] is None
    tr.update(info_trace(1, pos=(0.0, 67.0, 0.0)), frozenset(), {})
    assert tr.check()[0] == Status.SUCCESS


def test_visited_rule_remembers_past_positions():
    t = make_task(success=[{"visited": [10, 0, 0], "radius": 2}, {"visited": [0, 0, 10], "radius": 2}])
    tr = tracker_for(instantiate(t, 1, "dev"))
    tr.update(info_trace(1, pos=(10.0, 64.0, 0.0)), frozenset(), {})
    assert tr.check()[0] is None
    tr.update(info_trace(1, pos=(0.0, 64.0, 10.0)), frozenset(), {})
    assert tr.check()[0] == Status.SUCCESS


def test_events_filled_and_sorted():
    t = make_task(events=[{"at_s": 9, "commands": ["/b ~{dx}"]}, {"at_s": 2, "commands": ["/a"]}])
    spec = instantiate(t, 1, "dev")
    assert [e["at_s"] for e in spec.events] == [2, 9]
    assert spec.events[1]["commands"] == [f"/b ~{spec.values['dx']}"]


def test_derive_arithmetic():
    t = make_task(derive={"dx_p2": "dx + 2", "neg": "-dz"}, setup_commands=["/fill ~{dx} ~ ~ ~{dx_p2} ~ ~{neg}"])
    spec = instantiate(t, 4, "dev")
    v = spec.values
    assert v["dx_p2"] == v["dx"] + 2 and v["neg"] == -v["dz"]
    assert spec.commands[-1] == f"/fill ~{v['dx']} ~ ~ ~{v['dx'] + 2} ~ ~{-v['dz']}"


def test_suite_covers_categories_and_difficulties():
    from mcbench.tasks import CATEGORIES

    tasks = load_tasks()
    assert len(tasks) >= 20
    for c in CATEGORIES:
        assert sum(t.category == c for t in tasks.values()) >= 2, c
    assert {t.difficulty for t in tasks.values()} == {1, 2, 3}


def test_respawn_jump_counts_as_death():
    # MineStudio goes from the last damaged health straight to 20 on respawn, never 0.
    t = make_task(time_limit_s=10, success=[{"survive_s": 5}], failure=[{"dead": True}])
    tr = tracker_for(instantiate(t, 1, "dev"))
    tr.update(info_trace(3, health=0.38), frozenset(), {})
    assert tr.deaths == 0
    tr.update(info_trace(3, health=20.0), frozenset(), {})
    assert tr.deaths == 1 and tr.check() == (Status.MODEL_FAILURE, "dead")


def test_slow_regen_is_not_death():
    tr = tracker_for(instantiate(make_task(), 1, "dev"))
    for h in (12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0):
        tr.update(info_trace(1, health=h), frozenset(), {})
    assert tr.deaths == 0
