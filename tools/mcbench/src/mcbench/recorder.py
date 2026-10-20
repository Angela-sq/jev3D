"""Writes one folder per run: config, per-episode logs and frames, and results.csv."""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from mcbench.types import Action, ActMeta, EpisodeResult, Status

RESULT_FIELDS = [f.name for f in dataclasses.fields(EpisodeResult) if f.name != "extra"]


def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def provenance() -> dict:
    return {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": _cmd(["git", "rev-parse", "HEAD"]),
        "git_dirty": bool(_cmd(["git", "status", "--porcelain"])),
        "docker_image": _cmd(["docker", "image", "inspect", "mcbench-env", "--format", "{{.Id}}"]),
        "claude_version": _cmd([shutil.which("claude") or "claude", "--version"]),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
    }


def action_dict(a: Action) -> dict:
    d = dataclasses.asdict(a)
    d["keys"] = sorted(a.keys)
    return d


class EpisodeRecorder:
    def __init__(self, run: RunRecorder, path: Path):
        self.run = run
        self.path = path
        (path / "frames").mkdir(parents=True, exist_ok=True)
        for name in ("decisions.jsonl", "steps.jsonl"):
            (path / name).write_text("")

    def _append(self, name: str, obj: dict) -> None:
        with open(self.path / name, "a") as f:
            f.write(json.dumps(obj) + "\n")

    def decision(self, i: int, frame: np.ndarray, prompt: str, action: Action, meta: ActMeta, n_prev: int, n_new: int) -> None:
        frame_file = f"frames/{i:05d}.png"
        Image.fromarray(frame).save(self.path / frame_file)
        m = dataclasses.asdict(meta)
        self._append("decisions.jsonl", {
            "i": i, "frame": frame_file, "prompt": prompt, "action": action_dict(action),
            "n_prev": n_prev, "n_new": n_new, **m,
        })

    def steps(self, trace: list[dict], action: Action) -> None:
        a = action_dict(action)
        with open(self.path / "steps.jsonl", "a") as f:
            for t in trace:
                f.write(json.dumps({"action": a, **t}) + "\n")

    def finish(self, result: EpisodeResult) -> None:
        d = dataclasses.asdict(result)
        d["status"] = Status(result.status).value
        (self.path / "result.json").write_text(json.dumps(d, indent=2))
        self.run.append_row(d)


class RunRecorder:
    def __init__(self, root: Path, run_id: str, config: dict, provenance: bool = True):
        self.dir = Path(root) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        cfg_path = self.dir / "config.yaml"
        if not cfg_path.exists():
            prov = globals()["provenance"]() if provenance else {}
            cfg_path.write_text(yaml.safe_dump({"run_id": run_id, "config": config, "provenance": prov}, sort_keys=False))

    def episode_dir(self, task: str, seed: int, mode: str) -> Path:
        return self.dir / "episodes" / task / str(seed) / mode

    def episode(self, task: str, seed: int, mode: str) -> EpisodeRecorder:
        return EpisodeRecorder(self, self.episode_dir(task, seed, mode))

    def finished_status(self, task: str, seed: int, mode: str) -> Status | None:
        p = self.episode_dir(task, seed, mode) / "result.json"
        if not p.exists():
            return None
        return Status(json.loads(p.read_text())["status"])

    def append_row(self, d: dict) -> None:
        path = self.dir / "results.csv"
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RESULT_FIELDS, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow(d)
