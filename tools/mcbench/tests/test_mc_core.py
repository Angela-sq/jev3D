from mcbench.actions import ENV_KEYS, to_env_action
from mcbench.timing import steps_for
from mcbench.types import Action


def test_to_env_action_clamps_camera():
    a = to_env_action(Action(yaw=90, pitch=-45))
    assert a["camera"] == [-30.0, 30.0]


def test_to_env_action_has_all_keys():
    a = to_env_action(Action(keys=frozenset({"forward", "jump"}), attack=True, hotbar=3))
    for k in ENV_KEYS:
        assert k in a
    assert a["forward"] == 1 and a["jump"] == 1 and a["back"] == 0
    assert a["attack"] == 1 and a["use"] == 0
    assert a["hotbar.3"] == 1 and a["hotbar.1"] == 0


def test_noop_is_all_zero():
    a = to_env_action(Action.noop())
    assert all(v == 0 for k, v in a.items() if k != "camera")
    assert a["camera"] == [0.0, 0.0]


def test_steps_for_charged():
    assert steps_for("charged", 1.3, None) == (26, 0)
    assert steps_for("charged", 0.01, None) == (1, 0)


def test_steps_for_paused():
    assert steps_for("paused", 5.0, None) == (0, 10)


def test_steps_for_hold_override():
    assert steps_for("paused", 5.0, 3) == (0, 3)
    assert steps_for("charged", 0.5, 4) == (10, 4)
