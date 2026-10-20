# Minecraft macOS input probe

A small native Swift controller for the official launcher's Java game window.
It captures window pixels and sends ordinary key/mouse events. It does not read
Minecraft memory, entities, coordinates, world files, or game APIs, and contains
no aiming, navigation, or combat policy. OS window metadata is used only to
identify and focus the game.

## Build

From the repository root:

```sh
mkdir -p /tmp/minecraft-control-probe/cache
swiftc -module-cache-path /tmp/minecraft-control-probe/cache tools/minecraft-control/control.swift -o /tmp/minecraft-control-probe/mc-control
/tmp/minecraft-control-probe/mc-control status
```

Requires macOS, Swift command-line tools, and Screen Recording/Accessibility
permissions for the invoking application. In Codex the helper needed an approved
run outside the shell sandbox; inside it, permissions appeared false and no
windows were returned. This does not grant permissions or change macOS settings.

Use the actual `kCGWindowNumber` returned by `status`; IDs change on relaunch.
For example, replacing `WINDOW_ID`:

```sh
/tmp/minecraft-control-probe/mc-control capture WINDOW_ID /tmp/minecraft.png
/tmp/minecraft-control-probe/mc-control key WINDOW_ID escape 80
/tmp/minecraft-control-probe/mc-control key WINDOW_ID w 200
/tmp/minecraft-control-probe/mc-control look WINDOW_ID 100 100
/tmp/minecraft-control-probe/mc-control click WINDOW_ID left 50
```

Key/click durations are milliseconds, limited to 0–1000. Camera deltas are
limited to -200..200 per axis and are not degrees; response depends on game
sensitivity and mouse settings. Clicks target the window center, intended for
in-game attack/use rather than arbitrary menu buttons. Input brings Minecraft
forward, so do not use other applications during a control sequence. Escape is
a toggle: inspect the screenshot before using it to pause or resume.

Each operation prints JSON timestamps to stdout. These report dispatch/capture
completion, not guaranteed simulation receipt or exact render time. Use separate
log files per command or parse consecutive JSON objects. This is an input probe,
not yet a benchmark runner, simultaneous-input policy, video recorder, or
high-frequency model loop. It does not select or call an AI model.

## Validation on this Mac (2026-10-19)

Minecraft 26.3 singleplayer, official bundled Java runtime:

- Discovered the game by process and window metadata despite its empty runtime
  bundle identifier. Excluded launcher and hidden OpenGL utility windows.
- Captured the actual Minecraft window.
- Unpaused and paused with Escape; visually confirmed.
- Sent a 200 ms W input; the movement tutorial progress indicator advanced.
- Changed camera direction; visually confirmed in before/after screenshots.
- Sent left attack click; screenshot showed the hand swing/attack cooldown.
- Returned game to pause menu; no combat trials were run.

`NSRunningApplication.activate` alone did not focus this game. Setting the
Accessibility frontmost attribute and raising the window resolved focus.
Explicit mouse click-state metadata was necessary in the successful attack test.

Limitations: current support is restricted to a Java executable under the
standard `/minecraft/runtime/` path and a Minecraft-titled game window. Right
click, other key bindings, long sessions, and performance under combat have not
been validated. Abrupt process termination during a held event may leave input
held; the one-second duration bound only applies while the helper runs normally.
