import csv
import json

import numpy as np
import yaml

from mcbench.recorder import RunRecorder
from mcbench.types import Action, ActMeta, EpisodeResult, Status


def result(**kw):
    d = dict(task="t", category="combat", difficulty=1, seed=1, split="dev", mode="paused", agent="noop",
             status=Status.SUCCESS)
    d.update(kw)
    return EpisodeResult(**d)


def test_episode_folder_layout(tmp_path):
    rec = RunRecorder(tmp_path, "r1", {"a": 1}, provenance=False)
    ep = rec.episode("t", 1, "paused")
    ep.decision(0, np.zeros((4, 4, 3), dtype=np.uint8), "prompt", Action(keys=frozenset({"forward"})),
                ActMeta(latency_s=1.0, wall_s=1.2, calls=1, raw="{}"), n_prev=0, n_new=10)
    ep.steps([{"health": 20.0}] * 3, Action())
    ep.finish(result())
    d = tmp_path / "r1" / "episodes" / "t" / "1" / "paused"
    assert (d / "frames" / "00000.png").exists()
    dec = json.loads((d / "decisions.jsonl").read_text().splitlines()[0])
    assert dec["action"]["keys"] == ["forward"] and dec["latency_s"] == 1.0 and dec["n_new"] == 10
    assert len((d / "steps.jsonl").read_text().splitlines()) == 3
    assert json.loads((d / "result.json").read_text())["status"] == "success"


def test_results_csv_appends_one_row(tmp_path):
    rec = RunRecorder(tmp_path, "r1", {}, provenance=False)
    rec.episode("t", 1, "paused").finish(result())
    rec.episode("t", 2, "paused").finish(result(seed=2, status=Status.MODEL_FAILURE))
    rows = list(csv.DictReader(open(tmp_path / "r1" / "results.csv")))
    assert [r["status"] for r in rows] == ["success", "model_failure"]
    assert rows[1]["seed"] == "2"


def test_config_has_provenance_keys(tmp_path):
    RunRecorder(tmp_path, "r1", {"agent": {"type": "noop"}})
    cfg = yaml.safe_load(open(tmp_path / "r1" / "config.yaml"))
    for k in ("git_commit", "docker_image", "claude_version", "platform", "python", "created_utc"):
        assert k in cfg["provenance"]
    assert cfg["config"]["agent"]["type"] == "noop"


def test_finished_result_lookup(tmp_path):
    rec = RunRecorder(tmp_path, "r1", {}, provenance=False)
    assert rec.finished_status("t", 1, "paused") is None
    rec.episode("t", 1, "paused").finish(result(status=Status.INFRA_ERROR))
    assert rec.finished_status("t", 1, "paused") == Status.INFRA_ERROR
