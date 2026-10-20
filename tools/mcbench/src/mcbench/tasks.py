"""Task definitions: YAML loading, per-seed instantiation, and pass/fail rules.

Rules read privileged game info. They are used only for scoring, never sent to agents.
"""

from __future__ import annotations

import ast
import math
import operator
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TASK_DIR = Path(__file__).parent / "tasks"
CATEGORIES = (
    "navigation", "combat", "survival", "manipulation", "exploration", "planning", "adaptation",
)

# Every task starts with these, so mob spawns, weather, and time do not vary by accident.
# sendCommandFeedback goes first so later commands print nothing in the on-screen chat,
# which would leak coordinates and setup details into the pixels.
BASE_COMMANDS = [
    "/gamerule sendCommandFeedback false",
    "/gamerule logAdminCommands false",
    "/gamerule doMobSpawning false",
    "/gamerule doDaylightCycle false",
    "/gamerule doWeatherCycle false",
    "/weather clear",
    "/time set 6000",
]

ARENA_COMMANDS = [
    "/fill ~-15 ~-1 ~-15 ~15 ~-1 ~15 minecraft:grass_block",
    "/fill ~-15 ~ ~-15 ~15 ~8 ~15 minecraft:air",
    "/tp @s ~ ~ ~ 0 0",
]


@dataclass
class Task:
    id: str
    category: str
    difficulty: int
    goal_text: str
    setup_commands: list[str]
    time_limit_s: float
    success: list[dict]
    failure: list[dict]
    dev_seeds: list[int]
    heldout_seeds: list[int]
    params: dict = field(default_factory=dict)
    heldout_variant: dict | None = None
    arena: bool = True
    validated: bool = True
    oracle: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    derive: dict = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict) -> Task:
        return Task(
            id=d["id"],
            category=d["category"],
            difficulty=int(d["difficulty"]),
            goal_text=d["goal_text"],
            setup_commands=list(d.get("setup_commands", [])),
            time_limit_s=float(d["time_limit_s"]),
            success=list(d["success"]),
            failure=list(d.get("failure", [{"dead": True}, {"time_limit": True}])),
            dev_seeds=list(d["dev_seeds"]),
            heldout_seeds=list(d["heldout_seeds"]),
            params=dict(d.get("params", {})),
            heldout_variant=d.get("heldout_variant"),
            arena=bool(d.get("arena", True)),
            validated=bool(d.get("validated", True)),
            oracle=dict(d.get("oracle", {})),
            events=list(d.get("events", [])),
            derive=dict(d.get("derive", {})),
        )


@dataclass
class EpisodeSpec:
    """One task instantiated for one seed and split."""

    task: Task
    seed: int
    split: str
    goal_text: str
    commands: list[str]  # arena + task setup, run after BASE_COMMANDS and the chat fade
    success: list[dict]
    failure: list[dict]
    time_limit_s: float
    values: dict
    events: list[dict] = field(default_factory=list)  # [{"at_s": float, "commands": [str]}], scoring-side only


def load_tasks(task_dir: Path = TASK_DIR) -> dict[str, Task]:
    tasks = {}
    for p in sorted(task_dir.glob("*.yaml")):
        t = Task.from_dict(yaml.safe_load(p.read_text()))
        if t.category not in CATEGORIES:
            raise ValueError(f"{p.name}: unknown category {t.category!r}")
        tasks[t.id] = t
    return tasks


def sample_params(params: dict, rng: random.Random) -> dict:
    """Each param is {int: [lo, hi]}, {float: [lo, hi]}, {choice: [...]}, or
    {polar: {dist: [lo, hi], angle: [lo, hi]}} which yields <name>_dx and <name>_dz."""
    values = {}
    for name in sorted(params):
        spec = params[name]
        if "int" in spec:
            values[name] = rng.randint(*spec["int"])
        elif "float" in spec:
            values[name] = round(rng.uniform(*spec["float"]), 2)
        elif "choice" in spec:
            values[name] = rng.choice(spec["choice"])
        elif "polar" in spec:
            d = rng.uniform(*spec["polar"]["dist"])
            a = math.radians(rng.uniform(*spec["polar"]["angle"]))
            # Facing yaw 0 looks toward +z. Positive angle = to the player's right (-x).
            values[f"{name}_dx"] = round(-math.sin(a) * d)
            values[f"{name}_dz"] = round(math.cos(a) * d)
        else:
            raise ValueError(f"bad param spec for {name}: {spec}")
    return values


_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}


def arith(expr: str, values: dict):
    """Evaluate integer arithmetic like "dx + 2" over sampled values (names, ints, + - *)."""

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError(f"unsupported expression: {expr!r}")

    return ev(ast.parse(expr, mode="eval"))


def fill(x, values: dict):
    if isinstance(x, str):
        out = x.format(**values)
        if x.startswith("{") and x.endswith("}") and x.count("{") == 1:
            try:
                return float(out) if "." in out else int(out)
            except ValueError:
                return out
        return out
    if isinstance(x, list):
        return [fill(v, values) for v in x]
    if isinstance(x, dict):
        return {k: fill(v, values) for k, v in x.items()}
    return x


def instantiate(task: Task, seed: int, split: str) -> EpisodeSpec:
    d = {
        "goal_text": task.goal_text,
        "setup_commands": task.setup_commands,
        "success": task.success,
        "failure": task.failure,
        "params": task.params,
        "time_limit_s": task.time_limit_s,
        "events": task.events,
    }
    if split == "heldout" and task.heldout_variant:
        d.update(task.heldout_variant)
    values = sample_params(d["params"], random.Random(f"{task.id}:{seed}"))
    for name, expr in task.derive.items():
        values[name] = arith(expr, values)
    commands = (ARENA_COMMANDS if task.arena else []) + fill(d["setup_commands"], values)
    return EpisodeSpec(
        task=task,
        seed=seed,
        split=split,
        goal_text=fill(d["goal_text"], values),
        commands=commands,
        success=fill(d["success"], values),
        failure=fill(d["failure"], values),
        time_limit_s=float(d["time_limit_s"]),
        values=values,
        events=sorted(fill(d["events"], values), key=lambda e: e["at_s"]),
    )


def lookup(info: dict, path: str) -> float:
    cur = info
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return 0.0
        cur = cur[part]
    return float(cur) if isinstance(cur, (int, float)) else 0.0


def inventory_count(info: dict, name: str) -> int:
    inv = info.get("inventory") or {}
    return sum(
        int(slot.get("quantity", 0))
        for slot in inv.values()
        if isinstance(slot, dict) and name in str(slot.get("type", ""))
    )


OPS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


@dataclass
class RuleState:
    """What rules can see: the latest info plus harness-tracked facts."""

    info: dict
    spawn: tuple[float, float, float]
    pos: tuple[float, float, float]
    game_seconds: float
    time_limit_s: float
    dead: bool
    positions: list = field(default_factory=list)


def rule_holds(rule: dict, s: RuleState) -> bool:
    if "counter" in rule:
        return OPS[rule.get("op", ">=")](lookup(s.info, rule["counter"]), rule["value"])
    if "inventory" in rule:
        return OPS[rule.get("op", ">=")](inventory_count(s.info, rule["inventory"]), rule["value"])
    if "near" in rule:
        dx, dy, dz = rule["near"]
        tx, tz = s.spawn[0] + dx, s.spawn[2] + dz
        return math.hypot(s.pos[0] - tx, s.pos[2] - tz) <= rule["radius"]
    if "visited" in rule:
        dx, dy, dz = rule["visited"]
        tx, tz = s.spawn[0] + dx, s.spawn[2] + dz
        return any(math.hypot(p[0] - tx, p[2] - tz) <= rule["radius"] for p in s.positions + [s.pos])
    if "rise" in rule:
        return s.pos[1] - s.spawn[1] >= rule["rise"]
    if "dead" in rule:
        return s.dead
    if "survive_s" in rule:
        return not s.dead and s.game_seconds >= rule["survive_s"]
    if "time_limit" in rule:
        return s.game_seconds >= s.time_limit_s
    raise ValueError(f"unknown rule {rule}")


def rule_name(rule: dict) -> str:
    return next(iter(rule))
