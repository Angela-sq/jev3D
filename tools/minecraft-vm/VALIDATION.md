# Validation — 2026-10-19

Local setup/smoke tests, not model performance measurements.

| Check | Result |
|---|---|
| ARM64 Ubuntu VM boots with Apple VZ | Passed |
| Desktop and viewer survive full VM stop/start | Passed |
| Startup shortcut starts VM/launcher and opens viewer | Passed (exit 0) |
| Host HTTP viewer endpoint | 200 after restart |
| WebSocket VNC password authentication | Passed before and after restart |
| VNC framebuffer | 1280×720 |
| Viewer exposure | 127.0.0.1:6080 on host; VNC localhost in guest |
| Minecraft 26.3 official demo | Main menu and forest world loaded |
| Renderer | Vulkan software llvmpipe; OpenGL initialization failed |
| In-world FPS | Two F3 observations: 50 and 49 FPS at 854×480 |
| Forward movement | Scene position changed after W input |
| Camera control | View direction changed after relative mouse input |
| Inventory key | Inventory opened in captured frame |
| Menu clicks and Escape | Successfully navigated/paused/saved demo |
| Viewer-independent operation | Gameplay/control tests ran with no viewer connected |
| Short recording | 30-second MP4 captured in guest, copied to evidence/ |
| Controller bounds and release on interruption | 3 unit tests passed |
| Shell syntax | provision.sh, mcvm, start.command passed bash -n |
| Purchased game through Prism | Passed after owner completed Microsoft login; new VM Smoke Test world loaded |
| Licensed-world control check | Camera turn and inventory verified; F3 showed 60 FPS at 854×480 |
| Mob combat / PvP / model accuracy | Not tested |
| Six-hour gameplay soak | Not performed |

Prism 11.1.1 has a vanilla 26.3 instance configured for Java 25, up to 4096 MiB
heap and 854×480. The authenticated Prism launch and local world loading were
verified after the owner completed the Microsoft device login. Initial tests
used the separate built-in demo; the subsequent licensed test used Prism.
The owner authenticated directly; no password was saved in project files.

Guest action durations are not end-to-end model latency. They exclude model
inference and parts of host/tool overhead. For the experiment, timestamp the
full observation-to-action loop, disable evaluator debug overlays, fix the
world/gear/difficulty, and avoid pausing the world between model decisions.

The VM remains running with the licensed VM Smoke Test world paused. The native Mac Minecraft
world was left separate. No combat benchmark was scored, and these tests do
not establish anything about Astra or Jev's decision quality.
