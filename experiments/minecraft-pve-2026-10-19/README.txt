STATUS: ORIGINAL COHORT — FIRST-MOUSE-EVENT ISSUE FOUND AFTER RUN.
Use ../minecraft-pve-2026-10-19-v2/results.csv for the corrected cohort.
See CONTROL_ISSUE.txt. Original evidence is preserved.

Minecraft natural-terrain PvE pilot — 2026-10-19

Primary deliverable: results.csv
Each row is an attempted battle, including the three unscored calibrations.
Filter scored=True for the predeclared 36-battle evaluation. A pending row
is not a result. Check summary.json/completed_scored before using aggregates.

Evidence and reproduction
-------------------------
PROTOCOL.md defines the design and its limits. ACTOR_PROMPT.md is the fixed
combat instruction. schedule.json contains the randomized order and sites.
environment.json records the VM, client, model selection and input limits.
frozen-sha256.json covers the prompt, schedule, datapack and input code.
Controller hashes were added during early scoring; controller code was not
changed between calibration completion and the scored run.
CHANGES_BEFORE_SCORING.md records evaluator corrections during calibration.
evaluator-validation.txt contains separate forced win/death/timeout checks;
these are infrastructure tests, not agent victories or benchmark trials.

benchmark-world.tar.gz contains only the benchmark save, captured after
trial 4 with save-all flush. It contains no launcher account credentials.
Restore into a compatible Minecraft 26.3 saves directory; this save is
distinct from the user's original game. Next trial setup resets the player,
equipment and tagged opponents. Natural terrain is not flattened.

trials/trial-NNN/ contains:
- result.json: evaluator's raw terminal result and observed wall timestamps.
- events.log: authoritative Minecraft start/end events for the trial.
- actions.jsonl: requested inputs, execution times, screenshot hashes.
- transport.jsonl: host request/response timings and observation filenames.
- obs-NNNN.png: screenshots provided to the actor.
- terminal.png: evaluator screenshot after ending the trial.
- video.mp4: continuous 15-fps recording of the 854x480 game viewport.
- actor.json: selected actor identity and its final visual account.
- video.log, supervisor.log, complete: recording diagnostics/completion.

Videos and world archives are present locally but ignored by Git because
of size. A git push alone will not back up these large evidence files.

CSV interpretation
------------------
trial_id: schedule identifier; IDs 1–3 are calibration, IDs 4–39 scored.
site: A grassland terrace, B grassland slope, C grassland edge with foliage.
encounter: zombie, two_zombies, or skeleton.
repeat: predeclared replication index, not chronological order.
model/reasoning_effort: requested agent configuration, not latency estimates.
agent_task: canonical identity returned when the fresh actor was spawned.
outcome: win, death, timeout, technical, or pending.
game_seconds: active ticks divided by 20; excludes the five-second countdown.
wall_seconds: interval between supervisor observations of start/end events.
kills: player-attributed zombie plus skeleton kills during the trial.
health_remaining: health points (20 full health; two points per heart).
damage_taken_stat/damage_dealt_stat: raw Minecraft statistic counters;
preserved without a unit conversion or attribution to a particular enemy.
actions/observations: counts in the guest log, including countdown actions
and terminal observations. A late call after ending captures only a screenshot.
observation_to_action_*_ms: screenshot completion to next input-request
execution; includes model reasoning, tool orchestration and transport.
transport_median_ms: host request/response duration, including requested
action hold time. This is not model inference latency.
video/events/action_log: paths relative to this experiment folder.
technical_reason: transport/evaluator failure reason when applicable.
actor_note: actor's visible account, not authoritative scoring.

Calibration 1's raw health readback is 20 after immediate respawn. Its death
is authoritative; CSV and analysis report zero terminal health. The raw
result/event remain unchanged. The evaluator was fixed before scored trials.

Analysis and limits
-------------------
summary.json includes outcomes, descriptive Wilson 95% intervals, latency
summaries, evidence checks and missing IDs. The intervals do not account for
shared layouts or correlated failures. They are not population-level claims
about all Minecraft combat. Technical failures are counted separately and
excluded from the valid-trial win-rate denominator; none are silently removed.

The game runs while the model thinks. Each action lasts at most one second,
then movement/shield/attack are released. Long decision gaps therefore leave
the player idle and often unshielded. These results evaluate this complete
screenshot/action interface with the selected model. They cannot establish
that Astra lacks spatial reasoning, that Jev is better, or that latency alone
causes failure. No human, scripted, no-action or unlimited-time baseline is
included. Those are necessary follow-ups for causal comparisons.

Commands from the project root
------------------------------
python3 tools/minecraft-benchmark/collect.py
    Rebuild CSV from already collected local evidence.
python3 tools/minecraft-benchmark/collect.py N
    Collect a completed guest trial N and rebuild CSV. Requires running VM.
python3 tools/minecraft-benchmark/analyze.py
    Audit hashes/events/videos and refresh summary.json. Uses guest ffprobe.
python3 -m unittest discover -s tools/minecraft-benchmark -p 'test_*.py'
    Validate action restrictions, event parsing and input release on error.

The collector and analyzer do not choose combat actions. Do not invoke trial
setup while an actor is running. Trial directories refuse overwrite; reruns
need new identifiers and an explicitly documented new schedule.
