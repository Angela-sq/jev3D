Minecraft PvE initial benchmark

Primary corrected cohort: minecraft-pve-2026-10-19-v2/results.csv
Report and handoff: minecraft-pve-2026-10-19-v2/RESULTS.txt
36 trials: 0 wins, 32 deaths, 4 timeouts, 0 kills.

Original cohort: minecraft-pve-2026-10-19/
Retained separately with CONTROL_ISSUE.txt; do not pool with v2.

Videos and raw evidence are local within each cohort trials/ directory.
Videos are Git-ignored; a Git push alone does not back them up.

GitHub evidence download (all experiment files, including videos/world archive):
https://github.com/Angela-sq/jev3D/releases/tag/minecraft-pve-2026-10-19
The release also includes corrected-trial-011.mp4 for quick viewing.
Trial 11: movement/jump around 9 seconds, attack around 19–21 seconds.

Minecraft pixel-control benchmark (mcbench), Claude Fable 5.1
Results: minecraft-fable-2026-10-19/RESULTS.txt and report.pdf
19 tasks, one episode each: 3 passed, 16 failed (10 timeouts, 6 deaths).
Code: tools/mcbench/. Separate setup from the PvE cohorts; do not pool.

Standard PvE benchmark (10 mobs x 5), Claude Fable 5.1 — minecraft-pve-standard-2026-10-19/
Same prompt, controls and timing as the Astra v2 cohort, on a new VM. Results: RESULTS.txt.
50 trials (spiders at night, Amendment 1): 0 wins, 42 deaths, 3 timeouts, 5 target_lost.
Code: tools/minecraft-pve-standard/.
Not pooled with the Astra cohorts.
