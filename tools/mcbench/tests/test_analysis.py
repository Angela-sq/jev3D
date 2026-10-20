import json

import pytest

from mcbench.analysis import analyze, bootstrap_ci, load_results, summarize, wilson


def test_wilson_known_value():
    lo, hi = wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-3) and hi == pytest.approx(0.7634, abs=1e-3)
    assert wilson(0, 0) == (0.0, 0.0)


def test_bootstrap_deterministic():
    v = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert bootstrap_ci(v) == bootstrap_ci(v)
    lo, hi = bootstrap_ci(v)
    assert lo <= 4.0 <= hi


def row(status="success", **kw):
    d = dict(task="t", category="combat", difficulty=1, seed=1, split="dev", mode="paused", agent="a",
             status=status, reason="", steps=10, game_seconds=0.5, decisions=1, calls=1, input_tokens=100,
             output_tokens=10, format_errors=0, latency_mean_s=1.0, latency_p90_s=1.0, wall_latency_mean_s=2.0,
             final_health=20, damage_taken=0, damage_dealt=0, deaths=0, collisions=0, cost_usd_api_equiv=0.0)
    d.update(kw)
    return d


def test_summary_excludes_infra_and_truncated():
    rows = [row(), row(status="model_failure", seed=2), row(status="infra_error", seed=3),
            row(status="budget_truncated", seed=4), row(status="not_run", seed=5)]
    s = [g for g in summarize(rows, ["agent", "mode"])][0]
    assert s["n"] == 2 and s["successes"] == 1 and s["success_rate"] == 0.5
    assert s["infra_error"] == 1 and s["budget_truncated"] == 1 and s["not_run"] == 1


def write_run(tmp_path, rows):
    for r in rows:
        d = tmp_path / "episodes" / r["task"] / str(r["seed"]) / r["mode"]
        d.mkdir(parents=True)
        (d / "result.json").write_text(json.dumps(r))


def test_load_results_reads_result_json(tmp_path):
    write_run(tmp_path, [row(), row(seed=2, status="model_failure")])
    assert len(load_results(tmp_path)) == 2


def test_plots_and_tables_written(tmp_path):
    write_run(tmp_path, [row(), row(seed=2, status="model_failure"), row(seed=3, mode="charged"),
                         row(seed=4, split="heldout")])
    out = analyze(tmp_path)
    for name in ("success_by_category.pdf", "success_by_category.png", "success_by_difficulty.png",
                 "dev_vs_heldout.png", "charged_vs_paused.png", "summary.md", "summary.tex", "summary.csv"):
        assert (out / name).exists(), name
