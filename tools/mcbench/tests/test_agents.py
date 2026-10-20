import json

import numpy as np
import pytest

from mcbench.agents.fable import FableAgent, classify_result, parse_action, subprocess_env
from mcbench.types import Action, InfraError, Observation


def obs():
    return Observation(frame=np.zeros((36, 64, 3), dtype=np.uint8), goal="kill the zombie", step=0, game_seconds=0.0)


def result_event(text='{"keys": ["forward"], "attack": true}', model="claude-fable-5-1", api_ms=1300, **kw):
    ev = {
        "type": "result", "subtype": "success", "is_error": False, "result": text,
        "duration_ms": 2400, "duration_api_ms": api_ms, "total_cost_usd": 0.01,
        "usage": {"input_tokens": 5, "cache_creation_input_tokens": 700, "cache_read_input_tokens": 100, "output_tokens": 30},
        "modelUsage": {model: {}},
    }
    ev.update(kw)
    return ev


def fake_runner(event, stderr="", code=0):
    calls = []

    def run(args, stdin, env, timeout):
        calls.append({"args": args, "stdin": stdin, "env": env})
        lines = [json.dumps({"type": "system", "subtype": "init"})]
        if event is not None:
            lines.append(json.dumps(event))
        return code, "\n".join(lines) + "\n", stderr

    run.calls = calls
    return run


def test_parse_action_plain_json():
    a, err = parse_action('{"keys": ["forward", "jump"], "yaw": 12.5, "attack": true, "hotbar": 2}')
    assert not err
    assert a == Action(keys=frozenset({"forward", "jump"}), yaw=12.5, attack=True, hotbar=2)


def test_parse_action_in_code_fence():
    a, err = parse_action('Sure!\n```json\n{"keys": ["left"], "pitch": -5}\n```')
    assert not err and a.keys == frozenset({"left"}) and a.pitch == -5


def test_parse_action_prose_only_is_format_error():
    a, err = parse_action("I would walk forward toward the tree.")
    assert err and a == Action.noop()


def test_parse_action_drops_unknown_keys():
    a, err = parse_action('{"keys": ["forward", "fly"], "teleport": true, "use": true}')
    assert not err and a.keys == frozenset({"forward"}) and a.use


def test_parse_action_bad_types_is_format_error():
    a, err = parse_action('{"keys": "forward", "yaw": "left"}')
    assert err and a == Action.noop()


def test_env_has_no_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert "ANTHROPIC_API_KEY" not in subprocess_env()


def test_act_uses_stripped_flags_and_no_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    run = fake_runner(result_event())
    agent = FableAgent(workdir=tmp_path, runner=run)
    agent.reset("kill the zombie")
    a, meta = agent.act(obs())
    args = run.calls[0]["args"]
    for flag in ("--tools", "--strict-mcp-config", "--setting-sources", "--system-prompt", "--disable-slash-commands"):
        assert flag in args
    assert args[args.index("--model") + 1] == "claude-fable-5-1"
    assert "ANTHROPIC_API_KEY" not in run.calls[0]["env"]
    msg = json.loads(run.calls[0]["stdin"])
    kinds = [c["type"] for c in msg["message"]["content"]]
    assert kinds == ["image", "text"]
    assert a.keys == frozenset({"forward"}) and a.attack


def test_latency_uses_duration_api_ms(tmp_path):
    agent = FableAgent(workdir=tmp_path, runner=fake_runner(result_event(api_ms=1300)))
    agent.reset("g")
    _, meta = agent.act(obs())
    assert meta.latency_s == pytest.approx(1.3)
    assert meta.calls == 1
    assert meta.input_tokens == 805 and meta.output_tokens == 30


def test_model_identity_mismatch_raises(tmp_path):
    agent = FableAgent(workdir=tmp_path, runner=fake_runner(result_event(model="claude-sonnet-5-5")))
    agent.reset("g")
    with pytest.raises(InfraError) as e:
        agent.act(obs())
    assert e.value.kind == "model_identity" and e.value.stop_run


def test_rate_limit_is_infra_and_stops(tmp_path):
    ev = result_event(text="Claude AI usage limit reached|1760000000", is_error=True, subtype="error")
    agent = FableAgent(workdir=tmp_path, runner=fake_runner(ev))
    agent.reset("g")
    with pytest.raises(InfraError) as e:
        agent.act(obs())
    assert e.value.kind == "rate_limit" and e.value.stop_run


def test_no_result_event_is_cli_error(tmp_path):
    agent = FableAgent(workdir=tmp_path, runner=fake_runner(None, stderr="crash", code=1))
    agent.reset("g")
    with pytest.raises(InfraError) as e:
        agent.act(obs())
    assert e.value.kind == "cli" and not e.value.stop_run


def test_classify_auth_error():
    with pytest.raises(InfraError) as e:
        classify_result(result_event(text="Invalid API key · Please run /login", is_error=True), "")
    assert e.value.kind == "auth" and e.value.stop_run


def test_history_included_in_prompt(tmp_path):
    run = fake_runner(result_event(text='{"keys": ["forward"], "reason": "go to tree"}'))
    agent = FableAgent(workdir=tmp_path, runner=run, history=2)
    agent.reset("g")
    agent.act(obs())
    agent.act(obs())
    text = json.loads(run.calls[1]["stdin"])["message"]["content"][1]["text"]
    assert "go to tree" in text


def test_parse_action_click():
    a, err = parse_action('{"click": true, "attack": false}')
    assert not err and a.click and not a.attack


def test_prompt_version_is_v3(tmp_path):
    assert FableAgent(workdir=tmp_path, runner=fake_runner(result_event())).prompt_version == "mcbench-fable-prompt v3"


def test_parse_action_duration_to_steps():
    a, err = parse_action('{"keys": ["forward"], "duration": 0.5}')
    assert not err and a.hold_steps == 10
    assert parse_action('{"duration": 60}')[0].hold_steps == 100
    assert parse_action('{"duration": 0}')[0].hold_steps == 1
    assert parse_action('{"keys": []}')[0].hold_steps is None


def test_last_think_time_in_prompt(tmp_path):
    agent = FableAgent(workdir=tmp_path, runner=fake_runner(result_event()))
    agent.reset("g")
    assert "last decision took" not in agent.user_text(obs())
    agent.act(obs())
    assert "Your last decision took" in agent.user_text(obs())
