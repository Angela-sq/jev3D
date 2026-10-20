Minecraft pixel-control benchmark (mcbench): Claude Fable 5.1

Primary data: results.csv (one row per episode) and episodes/*/*/charged/result.json.
Read RESULTS.txt for the result, per-task outcomes and patterns.
Read report.pdf for the same results with first/last screenshots per task.

19 tasks in 7 categories (navigation, combat, survival, manipulation,
exploration, crafting, adaptation), one episode each on dev seed 1, run in
MineStudio 1.1.6 (Minecraft 1.16) inside Docker. Charged timing: the game
keeps running while the model thinks. Task definitions live in
tools/mcbench/src/mcbench/tasks/; the run config is run19.yaml and the
resolved config with provenance is config.yaml.

This is a separate setup from the PvE cohorts next to it (different game
version, harness, tasks and model). Do not pool.

Reproduce from tools/mcbench/:
  uv sync && ./docker/run.sh
  uv run mcbench run configs/run19.yaml --yes     # about 170-950 model calls
  uv run mcbench analyze runs/run19-v2
