# Jev with a self-evolved text harness (after MCJev) — 2026-10-26

A partial reproduction of Hao AI Lab's MCJev (https://haoailab.com/blogs/mcjev/) on our standard PvE fights.
MCJev's idea: a fast decision model (Jev) picks each move from a short multiple-choice question about the fight written
as text, a body runs the 50 ms reflexes, and an LLM coding agent (Claude) rewrites the harness between rounds by
reading the fight logs. Here Jev is TypeSafe's hosted Jev (`jev-preview`), not MCJev's DiffusionGemma (no NVIDIA GPU).
The agent that evolved the harness was Claude Opus 5.5 in a Claude Code session, with the owner overseeing.

## Loop (tools/minecraft-jev-harness/player.py, runs in the VM)
1. The `jevh` datapack prints the game state every tick into the game log: player and mob position, rotation and
   health, mob velocity, arrows nearby. Scoring is the standard evaluator's, unchanged.
2. A reader thread parses those lines.
3. A body thread runs every 50 ms: holds the chosen move's keys, aims at the mob, swings when the sword is charged
   and the mob is in reach, plus the harness's reflexes (`adjust`).
4. A head loop, every 0.2 s: the harness writes the facts as text (`describe`) and offers the moves that fit
   (`options`); Jev answers one choice question (options shuffled); the top choice goes to the body. With one
   option, Jev is not asked.
5. Every decision goes to `trials/trial-NNNN/steps.jsonl` (text, options, Jev's probabilities, choice).

## Harness evolution (dev set: the first standard fight of each of the 10 mobs)
Each version's docstring in `tools/minecraft-jev-harness/harness/vN.py` says what it lost and what changed.

| Version | Dev wins | Change |
|---|---|---|
| v1 | 4/10 | plain facts, the same 7 moves every time |
| v2 | 8/10 | sprint + jump on chases, zigzag, moves offered by distance, creeper fuse facts |
| v3 | 7/10 | spacing (hit, step back while recharging), creeper poke |
| v4 | 5/10 | swing only on target, aim ahead; faster turning overshot (regression) |
| v5 | 8/10 | aim corrects for turns the late state cannot show yet (Smith predictor) |
| v6 | 9/10 | swings blocked by leaves detected; creeper guard at 3.5 blocks |
| v7 | 9/10 | creeper fuse reflex (back off until the fuse runs down) |

## Evaluation: the 50 standard fights (same setups and order as Fable's benchmark)
See RESULTS.txt. v7 + Jev 43/50, v7 with random picks 40/50, v1 + Jev 30/50.

## Differences from the standard benchmark (read before comparing)
- Privileged state: the harness reads positions and health from the game; Fable and the screenshot Jev saw pixels only.
- The body aims and times swings by code; the model only picks the move.
- v7 was tuned on 10 dev fights whose setups are 10 of the 50 eval fights (same mob, site, repeat).
- A leftover AI-off stray tagged `pve_enemy` (from an earlier run) was removed before trial 2; trial 1 is the
  smoke fight that walked toward it.

## Files
- `runs.json`: every run (name, harness, set, trial IDs). `results.csv`, `summary.json`: one row per fight, totals.
- `trials/trial-NNNN/`: `steps.jsonl`, `jev.json` (tokens, clicks, click log), `result.json`, `events.log`, `actions.jsonl`.
- Videos and screenshots: release `minecraft-jev-harness-2026-10-26` (one tar per run); none are kept locally.

## Rerun
```sh
cd tools/minecraft-jev-harness
python3 run.py deploy
python3 run.py run v7 eval            # or: run v1 eval; run v7+random eval v7-random-eval
python3 run.py release minecraft-jev-harness-2026-10-26
```
