# mcbench: Minecraft 3D-control benchmark

mcbench measures how well a model controls a Minecraft player from pixels alone. It scores Claude Fable 5.1 (`claude-fable-5-1`) now, and is built so trained policies can be scored later through the same interface.

## Setup

Run every command from `tools/mcbench/`.

Requirements: Docker Desktop, `uv`, and the `claude` CLI logged in with a Claude subscription (`claude auth status` must show `"authMethod": "claude.ai"`).

```sh
uv sync
./docker/run.sh                 # builds the env image and starts it on 127.0.0.1:8765
curl -s http://127.0.0.1:8765/health        # {"ok": true, ...}
```

The first build downloads about 5 GB (Ubuntu, Java 8, PyTorch CPU, MineStudio). The Minecraft engine (~450 MB) is cached in `~/.cache/mcbench/minestudio`.

## Commands

```sh
uv run pytest tests                         # unit tests (no Docker, no model calls)
uv run mcbench validate [task ...]                  # check task rules in live Minecraft, no model calls
uv run mcbench estimate configs/full.yaml   # planned model calls
uv run mcbench smoke                                # small Fable run: 3 tasks, 1 seed, paused, <= 90 calls
uv run mcbench smoke --agent random                 # same, with a random agent (no model calls)
uv run mcbench run configs/full.yaml --yes  # full benchmark (needs --yes)
uv run mcbench analyze runs/<run_id>                # tables + plots into runs/<run_id>/analysis/
```

Re-running a config with the same `run_id` resumes it: finished episodes are skipped; `infra_error` and `not_run` episodes are retried.

## What a model sees and does

- **Sees:** one 640x360 screenshot, the task's goal sentence, elapsed game time, and (Fable only) how long its last decision took to think. Agents may keep their own memory. No game state (positions, inventory data, counters) ever reaches an agent; the harness builds the observation from the frame and goal text only (`tests/test_harness.py::test_agent_never_sees_info`).
- **Does:** one action per decision: movement keys held, camera turn (yaw/pitch, clamped to ±30° per decision), `click` (one fresh left click, for hitting mobs), `attack` (left button held, for breaking blocks), `use` (right button held), hotbar slot, inventory key press. Agents may also give a duration (`hold_steps`; Fable writes `"duration"` in seconds, up to 5 s): the action runs that long and then the player stands still with everything released until the next action starts.

`click` and `attack` are separate because Minecraft hits a mob only on a fresh press, while breaking a block needs the button held without release.

## Timing modes

Minecraft runs 20 steps per second. Every task runs in both modes.

- **Charged (headline).** The game is frozen while the model thinks; then the game runs `max(1, ceil(latency × 20))` steps with the model's previous action still applied (or standing still, if that action had a duration that already ran out). An action with a duration runs right after the think; one without stays held through the next think. Mobs keep moving and attacking during that time. Latency for Fable is the model time reported by `claude -p` (`duration_api_ms`), not CLI start-up; both are logged. Local policies are charged their wall time on this machine.
- **Paused.** The game waits for the model; each new action is held for its duration, or 10 steps (0.5 s) by default. This shows what the model could do if it were instant. The gap between the two scores is the cost of slowness.

## Tasks

20 tasks in 7 categories, difficulty 1-3. Each has 3 dev seeds and 2 held-out seeds; held-out episodes also use a held-out variant (different mob, layout, position range, or event timing). Definitions are in `src/mcbench/tasks/*.yaml`.

| Category | Tasks (difficulty) |
|---|---|
| navigation | navigate_landmark (1), navigate_climb (2), navigate_wall (3) |
| combat | combat_sheep (1), combat_zombie (2), combat_skeleton (3) |
| survival | survive_one_zombie (1), survive_mobs (2), survive_skeletons (3) |
| manipulation | collect_wood (1), mine_stone (2), build_pillar (2) |
| exploration | explore_behind (2), explore_visit_two (3) |
| planning | craft_planks (1), craft_table (2), craft_sticks (2), craft_pickaxe (3) |
| adaptation | adapt_target_moves (2), adapt_night_falls (3) |

Every episode:

1. Full world restart with the episode seed (about 50 s).
2. Base commands: command feedback off, mob spawning off, weather and day cycle frozen, time set to day.
3. 220 idle steps so any chat text fades from the screen (not scored).
4. Arena (flat 31x31 grass floor, cleared above) and task setup commands, with positions drawn from the seed.
5. 5 idle steps so the first frame shows the finished setup (not scored).
6. Play until a success rule, a failure rule, the time limit, or the call cap.

Pass/fail rules read game counters that the model never sees: `counter` (e.g. `kill_entity.zombie`), `inventory` (item count by name), `near` (horizontal distance to a spot relative to the start), `visited` (was near a spot at any time), `rise` (height above start), `survive_s`, `dead`, `time_limit`. Timed `events` run Minecraft commands mid-episode (adaptation tasks).

`mcbench validate` checks each task on its first dev seed: a do-nothing agent must not pass, and an oracle that forces the success condition with commands (or plays a scripted action) must pass. Results append to `docs/validation.md`.

## Episode statuses

| Status | Meaning | Scored |
|---|---|---|
| `success` | success rule met | yes |
| `model_failure` | died, time limit, or other failure rule (includes format errors) | yes |
| `budget_truncated` | episode hit its call cap first | no, counted separately |
| `infra_error` | env crash, HTTP failure, `claude -p` error (auth, rate/usage limit, CLI crash), model-identity mismatch | no, counted separately; retried on resume |
| `not_run` | run stopped early (budget or a stop-the-run error) | no; retried on resume |

## Budget and safety rails

- Caps per episode, per run, and across runs (`runs/ledger.json`). The run stops cleanly when a cap is hit.
- `mcbench run` prints planned calls and refuses above `confirm_threshold` without `--yes`.
- A usage/rate-limit or auth error from `claude -p` stops the run instead of retrying.
- Before a Fable run: `claude auth status` must report `authMethod: claude.ai`. Every call removes `ANTHROPIC_API_KEY` from the subprocess environment and checks that `modelUsage` lists exactly `claude-fable-5-1`.
- `claude -p` runs with tools, MCP servers, settings files, slash commands, and the default system prompt stripped (about 1.7k input tokens per call with a screenshot instead of about 31k).
- `cost_usd_api_equiv` is the CLI's API-price estimate. It is not billed on a subscription; it is logged only to show scale.

## Run folder

```
runs/<run_id>/
  config.yaml                 # resolved config + provenance (git commit, image id, claude version, platform)
  results.csv                 # one row per finished episode (append-only)
  episodes/<task>/<seed>/<mode>/
    result.json               # source of truth for analysis
    decisions.jsonl           # prompt, raw model text, parsed action, latency, tokens, step counts
    steps.jsonl               # one line per env step: action, health, position, gui flag
    frames/00000.png ...      # the screenshot the agent saw at each decision
  analysis/                   # summary.{md,tex,csv}, success_by_*.{pdf,png}
```

## Results so far (run19-v2, 2026-10-19)

Config: `configs/run19.yaml`. 19 tasks (every task except `collect_wood`, whose log pillar floats out of reach once the bottom log is broken), 1 dev seed each, charged mode, prompt `mcbench-fable-prompt v3`, cap 100 calls per episode. Results and evidence: `experiments/minecraft-fable-2026-10-19/`.

Fable passed 3 of 19: `mine_stone`, `build_pillar`, `explore_visit_two`. It failed all navigation, combat, survival, crafting, and adaptation tasks. Per-task results, a one-sentence reason for each failure, and start/end screenshots: `../../experiments/minecraft-fable-2026-10-19/report.pdf`. One episode per task gives only a rough picture.

## Assumptions and limitations

- **Not fully deterministic.** The same seed gives the same terrain and start position (checked in `docs/env-notes.md`), but Minecraft's mob AI and random ticks are not seeded. Results rely on several seeds, not exact replay.
- **Emulated Minecraft.** The env runs as x86 under emulation on Apple Silicon. Charged mode does not depend on emulation speed, because game time is advanced in steps computed from the model's latency.
- **Fable latency includes thinking.** Fable runs with `claude -p` defaults. In run19-v2 mean model time per decision was 2.4–9.3 s depending on the task (crafting was slowest). The prompt version is logged with every run (`mcbench-fable-prompt v3`).
- **One screenshot per decision.** Fable sees the current frame plus a text list of its own last 5 actions, not earlier frames.
- **Damage dealt is not available.** MineStudio 1.1.6 left `damage_dealt` empty in every episode, including ones where the agent killed a zombie. The field is still logged, but it is left out of the summary tables. Kills are counted from `kill_entity`; damage taken is computed from health drops.
- **Deaths are read from health.** MineStudio never reports health 0: on death health jumps from the last damaged value straight to 20 at respawn. The tracker counts a death when health is 0 or jumps by more than 4 to full in one step.
- **Collisions are approximate:** counted when forward is held and the player moves less than 0.05 blocks over 4 steps.
- **On-screen hints.** Minecraft's tutorial and advancement pop-ups appear in the top-right corner. They are the same for every agent and reveal no hidden state.
- **Arena tasks.** Most tasks run in a flattened 31x31 arena so random terrain cannot hide the goal; world seeds still change the surrounding scenery and biome.
- **Validation is an oracle check, not a solvability proof.** An oracle passing shows the rule fires; it does not show the task is solvable by play within the time limit.
- **Usage limits.** Subscription usage limits are not visible to the harness. A limit error stops the run; resume later with the same `run_id`.
