# Calibration and evaluator changes

All changes below occurred before the first scored trial.

- Dedicated benchmark world copied from VM Smoke Test, seed
  -6257074856933950438. Natural ground blocks were not flattened or built over.
- Use Adventure mode to prevent terrain edits during repeated encounters.
- Count zombie/skeleton player kills rather than generic mob kills, so an
  incidental passive-animal kill cannot satisfy an encounter objective.
- Calibration 1 found that immediate respawn can reset Health to 20 before
  the death event is formatted. Death terminal health is now explicitly zero;
  calibration 1's raw event remains unchanged, and its CSV health is corrected
  from outcome=death. The original readback is not interpreted as survival.
- Enemy spawn height uses the motion-blocking heightmap, including foliage,
  to avoid spawning inside leaves at the wooded site. Player starts use the
  motion-blocking-no-leaves heightmap, at the surveyed clear start positions.
- The input interface releases keys/buttons after each bounded action. It
  does not maintain shield/blocking or movement during reasoning. This is a
  material limitation, disclosed in the protocol, not a pure model metric.
- No combat prompt was tuned based on the calibration loss.
