# Natural-terrain PvE pilot

## Question and scope
Can GPT-6 Astra control vanilla Minecraft 26.3 from screenshots and basic
keyboard/mouse actions quickly enough to win short mob encounters? This is
an initial systems/agent benchmark, not an estimate of general spatial intelligence.
No Jev comparison is included. User explicitly authorized a GPT-6 Astra subagent.

## Predeclared design
- Target: 36 scored trials: 3 natural-terrain sites × 3 encounter types × 4 repeats.
- Encounters: one adult zombie, two adult zombies, one skeleton.
- Adventure mode (prevents terrain edits), normal difficulty, full health/hunger, fresh iron armor, iron sword,
  offhand shield; no healing consumables; 90 seconds of game time maximum.
- Natural blocks/height variation remain intact. No flat constructed floor.
  A world border defines the arena; reset player/mobs/equipment between trials.
- Fixed daylight; undead receive helmets to prevent sunlight damage.
- Disable natural spawning, weather/time changes, natural healing, and mob griefing.
- Randomized balanced order, fixed schedule seed 20261019. Publish all trials.
- Up to three unscored calibration battles before scored trials. Freeze agent
  prompt and environment after calibration; label any later protocol changes.
- Win requires all assigned mobs killed by player, without player death.
  Death takes precedence over simultaneous kill. Timeout is failure to finish
  within the limit. Technical failures remain rows and are not silently dropped.

## Separation
The evaluator may use game commands, entity tags, scoreboard counters and
logs to reset and score. It must not calculate or choose combat actions.
The Astra actor receives only screenshots and the fixed public task prompt,
and emits bounded keyboard/mouse actions. No chat commands, game-state reads,
debug overlays, reach calculations, auto-aim, target tracking or scripted fighting.
Game continues while the actor thinks. No between-action pausing or slowed ticks.
Model: gpt-6-astra, reasoning effort medium. Record the returned agent ID for each trial. Each scored trial uses
a fresh actor context with the same prompt, to avoid cross-trial coaching.

## Evidence and analysis
Save one CSV row per attempted trial, authoritative start/end events, action
logs, timestamped observations and a video. Record outcome, kills, duration,
remaining health, damage statistics, tool errors and observation/action counts.
Report overall and per-encounter win rates with Wilson 95% intervals, plus
timeouts, deaths, technical failures, and latency summaries. These intervals
describe this small fixed scenario set; repeated layouts are not independent
samples of all Minecraft terrain. Record FPS/host-load limitations separately.

## Execution plan
1. Copy the smoke-test world into a separate benchmark world; enable setup
   commands only there. Survey and freeze three natural sites.
2. Build and validate a datapack for deterministic setup and terminal scoring;
   test victory, death and timeout paths without involving scored actors.
3. Add bounded simultaneous controls, capture/recording and CSV collection;
   test release-on-error, timeout and evidence completeness.
4. Run calibration, freeze assets/prompt/schedule, then run all 36 attempts.
5. Audit every row against events/video; save analysis and reproducibility files.

Implementation proceeds under the user's explicit end-to-end authorization.
No extra design approval requested. No experiment outcome is assumed in advance.

## Frozen controller design
Each decision may move the camera up to 300 pixels per axis and hold any
combination of WASD, jump, sprint, sneak, sword-slot selection and mouse
buttons for at most 1000 ms. Inputs release afterward, including while the
model thinks. No repeated attack loop or conditional policy is implemented.
This bounded-action interface introduces idle time; results measure this
interface plus the model, not an unrestricted continuous-control agent.
A five-second pre-fight countdown permits the first screenshot before mobs
activate. All trials use the same countdown. Actor starts its own trial.
