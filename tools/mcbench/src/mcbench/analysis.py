"""Turns a run folder into summary tables, confidence intervals, and plots.

Each episode's result.json is the source of truth (results.csv can hold older
rows for episodes that were re-run after an infra error).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

SCORED = ("success", "model_failure")
UNSCORED = ("infra_error", "budget_truncated", "not_run")
# damage_dealt is left out: MineStudio 1.1.6 reported it empty in every episode, even after kills.
METRICS = ("game_seconds", "final_health", "damage_taken", "collisions", "decisions", "calls",
           "input_tokens", "output_tokens", "latency_mean_s", "format_errors")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def bootstrap_ci(values, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    means = rng.choice(v, size=(n, len(v)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def load_results(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(run_dir).glob("episodes/*/*/*/result.json"))]


def summarize(rows: list[dict], by: list[str]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in by), []).append(r)
    out = []
    for key in sorted(groups, key=lambda k: tuple(str(x) for x in k)):
        g = groups[key]
        scored = [r for r in g if r["status"] in SCORED]
        k = sum(r["status"] == "success" for r in scored)
        n = len(scored)
        lo, hi = wilson(k, n)
        s = dict(zip(by, key))
        s.update(n=n, successes=k, success_rate=(k / n if n else 0.0), ci_lo=lo, ci_hi=hi)
        for u in UNSCORED:
            s[u] = sum(r["status"] == u for r in g)
        for m in METRICS:
            vals = [float(r.get(m, 0) or 0) for r in scored]
            s[f"{m}_mean"] = float(np.mean(vals)) if vals else 0.0
            s[f"{m}_ci"] = bootstrap_ci(vals)
        out.append(s)
    return out


def _bar(ax, groups: list[dict], label_keys: list[str], title: str) -> None:
    labels = [" / ".join(str(g[k]) for k in label_keys) for g in groups]
    rates = [g["success_rate"] for g in groups]
    err = [[g["success_rate"] - g["ci_lo"] for g in groups], [g["ci_hi"] - g["success_rate"] for g in groups]]
    x = np.arange(len(groups))
    ax.bar(x, rates, yerr=err, capsize=4, color="#4C72B0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("success rate (Wilson 95% CI)")
    ax.set_title(title, fontsize=10)
    for i, g in enumerate(groups):
        ax.text(i, 0.02, f"n={g['n']}", ha="center", fontsize=7, color="black",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})


def make_plots(rows: list[dict], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plots = {
        "success_by_category": (["agent", "mode", "category"], "Success by skill category"),
        "success_by_difficulty": (["agent", "mode", "difficulty"], "Success by difficulty"),
        "dev_vs_heldout": (["agent", "mode", "split"], "Dev vs held-out"),
        "charged_vs_paused": (["agent", "mode"], "Charged (live speed) vs paused"),
    }
    for name, (by, title) in plots.items():
        groups = summarize(rows, by)
        fig, ax = plt.subplots(figsize=(max(4, 0.6 * len(groups) + 2), 3.5))
        _bar(ax, groups, by, title)
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(out / f"{name}.{ext}", dpi=200)
        plt.close(fig)


def write_tables(rows: list[dict], out: Path) -> None:
    groups = summarize(rows, ["agent", "mode", "split", "category"])
    cols = ["agent", "mode", "split", "category", "n", "successes", "success_rate", "ci_lo", "ci_hi",
            "infra_error", "budget_truncated", "not_run", "game_seconds_mean", "damage_taken_mean",
            "calls_mean", "latency_mean_s_mean", "format_errors_mean"]
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(groups)

    def fmt(g, c):
        v = g[c]
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    md += ["| " + " | ".join(fmt(g, c) for c in cols) + " |" for g in groups]
    (out / "summary.md").write_text("\n".join(md) + "\n")

    tex_cols = ["agent", "mode", "split", "category", "n", "success_rate", "ci_lo", "ci_hi"]
    tex = ["\\begin{tabular}{" + "l" * 4 + "r" * 4 + "}", "\\toprule",
           " & ".join(c.replace("_", "\\_") for c in tex_cols) + " \\\\", "\\midrule"]
    tex += [" & ".join(fmt(g, c).replace("_", "\\_") for c in tex_cols) + " \\\\" for g in groups]
    tex += ["\\bottomrule", "\\end{tabular}"]
    (out / "summary.tex").write_text("\n".join(tex) + "\n")


def analyze(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    rows = load_results(run_dir)
    out = run_dir / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    write_tables(rows, out)
    make_plots(rows, out)
    print(f"{len(rows)} episodes -> {out}")
    return out
