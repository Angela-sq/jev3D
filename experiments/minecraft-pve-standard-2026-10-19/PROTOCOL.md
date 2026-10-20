# Standard PvE benchmark — Fable 5.1

## Question and scope
Can Claude Fable 5.1 kill single hostile mobs in vanilla Minecraft 26.3 from screenshots and
basic keyboard/mouse actions, in real time? Same task semantics, prompt, controls, timing and
evidence as the GPT-6 Astra v2 cohort (`../minecraft-pve-2026-10-19-v2`), widened to 10 mob types.
This cohort is not pooled with the Astra cohorts (different mobs, schedule, VM and driver).

## Predeclared design
- 50 scored trials: 10 mobs × 5 repeats. Mobs: zombie, husk, skeleton, stray, spider,
  cave_spider, creeper, witch, pillager, vindicator. One mob per trial.
- Sites: the three natural-terrain sites of the Astra world (A 240.5,-240.5; B 270.5,-210.5;
  C 215.5,-190.5), restored from the Astra `benchmark-world.tar.gz`. Mob i, repeat r uses site
  (i+r) mod 3, so each mob sees every site (2/2/1) and the totals are 17/17/16.
- Order: shuffled with fixed seed 20261019 (`schedule.json`). Fresh actor per trial.
- Player: adventure mode, normal difficulty, full health and hunger, iron sword (slot 1), shield
  (offhand), full iron armor; no consumables; natural regeneration off.
- Mob: spawned 8 blocks south of the player on the motion-blocking surface, facing the player,
  AI off during a 5-second countdown. Fixed gear: leather helmet (unbreakable) on zombie,
  skeleton and stray; bow on skeleton and stray; crossbow on pillager; iron axe on vindicator;
  every other equipment slot empty; no effects.
- Arena: 40-block world border centred on the site (border damage 0). Fixed noon, clear weather.
  Natural, monster, patrol, wandering-trader and phantom spawning off; mob griefing off.
  Every non-player entity within 80 blocks is removed at setup and again when the fight starts.
- 90 seconds of game time (1800 ticks) from "FIGHT".

## Outcomes (evaluator datapack; checked every tick in this order)
1. death — the player died (wins ties).
2. win — the player killed the assigned mob (`minecraft.killed:<mob>` statistic).
3. target_lost — the mob no longer exists but the player did not kill it (creeper explosion, …).
4. timeout — 1800 ticks without one of the above.
5. technical — no terminal event within 125 wall seconds, or the actor never began.
All but technical count in the win-rate denominator. A technical trial is rerun once under
ID 100+n with the same condition; the rerun replaces it in the analysis. Usage-limit, auth or
wrong-model errors stop the whole run.

## Actor (Fable 5.1)
- `claude -p --model claude-fable-5-1 --effort medium`, one fresh session per trial, started from
  an empty temporary directory with `--setting-sources ""`, an empty MCP config, no slash commands.
- Tools: Bash, allowed only for `python3 <repo>/tools/minecraft-pve-standard/actor.py …`, and Read,
  allowed only for that trial's `obs-*.png` screenshots. Every tool call is audited afterwards.
- Prompt: `ACTOR_PROMPT.md`, the Astra v2 prompt with only the tool paragraph rewritten for
  Claude Code tools (Bash/Read instead of Codex exec/view_image).
- Controls (unchanged from v2): keys w,a,s,d,space,Shift_L,Control_L,1; mouse 1 (attack) and
  3 (shield); hold 0–1000 ms, then release; camera dx/dy ±300 px (100 px = 15°). A setup-only
  1-pixel mouse event absorbs Minecraft's ignored first mouse event.
- The game keeps running while the model thinks.

## Evidence (per trial, `trials/trial-NNN/`)
video.mp4 (15 fps, 854×480), every screenshot given to the actor, actions.jsonl, events.log,
result.json, transport.jsonl, terminal.png, transcript.jsonl (full actor session), actor.json.
`results.csv` has one row per attempt; `summary.json` holds the audit and aggregates.

## Analysis
Win rate overall, per mob and per site with Wilson 95% intervals; counts of each outcome;
secondary: damage dealt statistic, survival time; latency (observation-to-action median/max).
Five trials per mob gives wide per-mob intervals.

## Environment
Lima VZ VM, Ubuntu 24.04 ARM64, 8 vCPU, 12 GiB, Xvfb 1280×720, Vulkan llvmpipe (Mesa 25.2.8);
Minecraft 26.3, Java 25, Prism 11.1.1, window 854×480; render distance 4, simulation distance 5,
max FPS 60, pause on lost focus off, tutorial hints off, mouse sensitivity default (0.5).
At render distance 4 the 40-block border is drawn as faint diagonal stripes, as in the Astra
screenshots.

## Validation before scoring (no model calls)
`validate.py`: each mob at each site is set up, inspected and screenshotted, and ended by a forced
win, target loss or death; plus same-tick ties (kill+death → death; loss+death → death), a natural
creeper explosion (→ target_lost) and a timeout. Results: `validation/validation.json`.
Then one unscored Fable calibration trial (ID 901). Then hashes are frozen (`frozen-sha256.json`).

## Amendment 1 (2026-10-20, after the 50 scored trials)
Finding: spiders and cave spiders are neutral in daylight. With the arena fixed at noon, all 10
spider/cave_spider trials timed out with zero damage taken, so they did not test combat.
Change, for spider and cave_spider only: setup sets the time to midnight, and at "FIGHT" the
player gets night vision (icon hidden) so screenshots stay readable. Every other mob still
fights at noon (now also set explicitly per trial). The same 10 conditions (mob, site, repeat)
run again as trials 200+n; 300+n is the single technical rerun. In the analysis, trial 200+n
replaces trial n; the 10 daylight trials stay in results.csv with their original outcomes.
Prompt, controls, limits and model settings are unchanged. Spider validation at night: the player
took damage (117 and 191 stat units in 15 s, versus 0 in all daylight trials). The world border
stripes are more visible against the night sky. Hashes before this change: frozen-sha256-v1.json.
