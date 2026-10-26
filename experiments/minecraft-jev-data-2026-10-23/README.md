# Jev plays the standard PvE fights (data collection) — 2026-10-23

Jev (TypeSafe System One, `jev-preview` = jev-1.14.0) picks every action from the screenshot.
Goal: record screenshot → action → result data for training a fast Minecraft policy. Not a scored benchmark run.

## Loop (tools/minecraft-jev-data/jev_player.py, runs inside the VM)
1. Wait for the fight to start (end of the 5 s countdown).
2. Take a screenshot (854×480).
3. Ask Jev three questions about it: which action (choice), is a mob visible (yes/no), where is the mob (box).
   The action options are shuffled every call, because Jev leans toward the first option.
4. Sample one action from Jev's probabilities.
5. Play the action, then release all inputs.
6. Record the damage dealt/taken that the game reported before the next screenshot (`PVE_HIT` events).
7. Repeat until the evaluator ends the fight.

Actions (100 px of mouse = 15°): forward (w 400 ms), back (s 400 ms), turn_left/turn_right (±100 px),
attack (click), charge (w 250 ms, then click), shield (right button 500 ms).
Each action has a written rule that Jev reads (see `jev.json` in each trial).

## Fights
Same setups as the standard benchmark (`experiments/minecraft-pve-standard-2026-10-19`): same 10 mobs,
3 sites, gear, 90 s limit, same order; spiders at night (Amendment 1). Only the trial ID changes.
- pilot: 401–405, 5 zombie fights.
- batch, batch2, batch3, batch4: 501–550, 601–650, 701–750, 801–850 (the 50 standard fights, 4 times).

## Differences from the Fable/Astra runs
- Jev decides ~1.4–1.8 times per second (median Jev reply ~0.2 s) instead of every 5–8 s.
- The chat is hidden on screen (`chatScale:0.0`) from the batches on; the pilot screenshots show chat.
- pilot and batches 1–3 sample the action from Jev's probabilities (varied data); batch4 plays Jev's top choice (a clean score).
- Every attempt is kept; nothing is re-run.

## Files
- `results.csv`, `summary.json`: one row per fight, totals.
- `trials/trial-NNN/steps.jsonl`: one line per step: screenshot name, Jev probabilities, choice, sampled action,
  mob box, hits during the step.
- `trials/trial-NNN/`: screenshots, `actions.jsonl`, `events.log`, `result.json`, `terminal.png`, `video.mp4` (not in git).

## Rerun
```sh
cd tools/minecraft-jev-data
python3 run.py deploy          # builds and loads the datapack, copies scripts and the key file
python3 run.py pilot batch     # runs any fight not yet attempted
python3 run.py summary
```
The key is read from `~/.config/typesafe/api_key` (never committed).
