Corrected Minecraft PvE cohort (v2)

Primary data: results.csv. Trials 1–36 are scored; no calibration rows are pooled.
COMPLETE: summary.json reports completed_scored=36 with no audit errors.
Read RESULTS.txt for the final result, timing limitations and VM handoff.

Same 36-condition randomized order as original scored trials 4–39; same
combat prompt semantics, limits, gear and natural sites. Only setup input
initialization changed: a one-pixel event consumes Minecraft's ignored first
mouse event after setup chat closes. This does not choose an action or move
the camera in the verified setup. Three directional tests then registered
100 pixels as 15 degrees, with F3 screenshots retained in the original
cohort camera-diagnostic directory. Zero-pixel priming did not work.

Read PROTOCOL.md for the pre-run amendment. The original cohort remains
in ../minecraft-pve-2026-10-19 with CONTROL_ISSUE.txt. Do not pool cohorts.
The original README.txt describes CSV fields and evidence structure, which
are unchanged here. Use tools/minecraft-benchmark-v2/ for collection/audit.

Important: one-second bounded actions still release during reasoning.
Observation-to-action timing includes inference, orchestration and transport.
The resulting win rate measures this complete system, not isolated model
reasoning. No human, Jev, scripted or unlimited-time comparator is included.

All raw videos, screenshots, actions, events and actor notes live in trials/.
Videos remain local and Git-ignored; pushing the repo alone does not back them up.
The archived original benchmark world can reproduce arena geometry.
