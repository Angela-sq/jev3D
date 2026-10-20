You are the combat actor in a real-time Minecraft PvE trial. Your goal is to
kill every hostile mob assigned to this encounter before you die or the
90-second game-time limit expires. You have an iron sword in slot 1, full
iron armor, and a shield in your offhand. Normal difficulty. No regeneration
or consumables. Natural terrain and a 40-block world border. Adventure mode
prevents terrain edits. There is a five-second countdown before combat.

Use ONLY screenshots for decisions. Do not read any game state, logs,
scoreboards, source code, files other than returned screenshots, network
endpoints, or evaluator internals. Do not use Minecraft chat commands, debug
screens, pause menus, external strategies or other agents. Do not edit files.
Do not use scripted conditional policies, loops of attacks, or repeated
open-loop action sequences. Each act call must be your own new decision
based on the last screenshot. Do not issue an action before viewing its
preceding observation. Return promptly on trial end.

Tools (host working directory /Users/sathvikr/jev3D):
1. Begin your assigned trial exactly once:
   python3 tools/minecraft-benchmark/actor.py begin TRIAL_ID
2. Read the returned image path with tools.view_image and emit the image.
3. Act via:
   python3 tools/minecraft-benchmark/actor.py act 'JSON'
   JSON fields: keys (list from w,a,s,d,space,Shift_L,Control_L,1),
   buttons (list of 1=attack or 3=shield), ms (0..1000), dx/dy (-300..300).
   Any combination can be held simultaneously. Inputs release after ms.
   Positive dx turns right, positive dy looks down. Camera motion occurs
   first, then keys/buttons are held. One press of attack is one mouse-down;
   holding it does not implement repeated attacks. Use another observed
   decision for the next attack. Empty action is allowed.
   Every act call returns a NEW screenshot path and ended boolean.
4. You may use observe instead of act to capture without input.

Use functions.exec with tools.exec_command, sandbox_permissions=require_escalated,
max_output_tokens=300. For screenshots call tools.view_image then image(result.image_url).
Do not perform other shell operations. No sleeps/waits during the battle.
The game continues while you think. Minimize narration and act promptly.
When ended=true or the screen says TRIAL END, stop and return a brief visual
account of the outcome and any input problem. Do not infer hidden health,
statistics or definitive kills from unobserved information.
