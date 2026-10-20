# Minecraft VM — morning handoff

This is a separate Ubuntu ARM64 desktop inside Lima's Apple Virtualization VM.
Minecraft runs on its own virtual display, so guest screenshots and inputs do
not require bringing Minecraft to the foreground on your Mac. You can close
the browser viewer and use your other apps. Keep the Mac awake, plugged in,
and the lid open while an experiment runs.

The Microsoft account is now connected. The purchased game and a local test
world have been verified; skip sign-in below unless Prism requests it again.
See VALIDATION.md for the current test results.

## Start and sign in

1. Double-click `start.command` in this folder. It starts the existing VM,
   opens Prism Launcher, prints your local viewer password in Terminal, and
   opens <http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale>.
2. Enter that viewer password. It is a local VNC password, not your Microsoft
   password. Keep it private. Classic VNC uses its first eight characters.
3. In Prism, use **Add Microsoft account** in the initial setup, or
   **Accounts → Manage Accounts → Add Microsoft**. Complete Microsoft's login
   yourself with the account that owns Minecraft. If the VM cannot open a
   browser, use the displayed Microsoft device-login URL/code on your Mac.
4. Select the existing **26.3** instance and click **Launch**. Prism may download
   its own game libraries/assets on this first authenticated launch.
5. The authenticated instance and natural-terrain combat world are already configured. Open **Astra Natural PVE** if the world is not already loaded. See the benchmark records below before starting another trial.

If double-clicking is inconvenient, run in the Mac terminal:

```sh
cd /Users/sathvikr/jev3D
bash tools/minecraft-vm/start.command
```

The VM is installed at `~/.lima/minecraft-lab`. Do not delete it to restart.
The purchased-game instance is separate from the demo used for smoke tests.
No Microsoft credentials were copied from the Mac.

Benchmark records are in `experiments/minecraft-pve-2026-10-19-v2/`. Its
`results.csv` is the corrected cohort; `summary.json` gives the current completed
count. The original cohort in `experiments/minecraft-pve-2026-10-19/` is retained
with a documented first-mouse-event issue and must not be pooled with v2.
Use `tools/minecraft-benchmark-v2/` for scored trials, rather than the generic
manual controls below. Do not interrupt an active benchmark via the viewer.

## Configuration

| Item | Setting |
|---|---|
| VM | minecraft-lab; Ubuntu 24.04 ARM64; Lima 2.2.0; Apple VZ |
| Resources | 8 vCPUs, 12 GiB RAM, 48 GiB disk |
| Desktop | Xvfb :99, 1280×720; Openbox |
| Game | Vanilla Minecraft 26.3; Java 25; 854×480 window |
| Graphics | Mesa software Vulkan (llvmpipe), not GPU passthrough |
| Pilot settings | Render distance 4, simulation distance 5, max FPS 60 |
| Input | X11 keyboard/mouse; action holds limited to one second |
| Host shares | None |
| Viewer | Password-protected noVNC; host 127.0.0.1:6080 only |

The isolated game uses CPU rendering. Host workloads can still affect guest
latency/FPS because CPU and RAM are shared. For scored comparisons, keep host
load consistent and record frame rate and action latency. The ~49–50 FPS
observed in a simple demo forest is not a combat-performance guarantee.

## Agent controls

Run these on the host, from the repository. They target only the guest desktop:

```sh
tools/minecraft-vm/mcvm status
tools/minecraft-vm/mcvm capture /tmp/frame.png
tools/minecraft-vm/mcvm key w 200
tools/minecraft-vm/mcvm look 50 -10
tools/minecraft-vm/mcvm click 1 50
tools/minecraft-vm/mcvm release
```

`point X Y` is for menu interaction. `look DX DY` is relative camera motion.
Inputs act on the focused **guest** window; ensure Minecraft owns guest focus.
Screenshots are desktop pixels, not structured game state. The controller does
not choose actions, calculate reach, read entities, or implement combat logic.
Action timestamps are written to `~/minecraft-lab/control.jsonl` in the guest.
An immediately following screenshot can precede a rendered game response;
do not confuse command completion with the next game frame.

Use `mcvm key Escape 150` to pause during setup; do not pause between decisions
in a real-time scored trial. Use `mcvm stop` to stop the VM after saving/quitting
the game, and `mcvm start` plus `mcvm launcher` to bring it back.

## Setup and test files

- `minecraft-vm.yaml`: resource allocation and loopback-only forwarding.
- `provision.sh`: guest packages, persistent desktop/viewer services, Prism.
- `control.py`: pixel capture and bounded keyboard/mouse input.
- `check-viewer.py`: password authentication over the viewer WebSocket.
- `test_control.py`: input bounds and interruption-release tests.
- `prepare-demo.py`, `run-demo.py`: official built-in demo compatibility test;
  ARM native libraries come from Maven Central with checksum verification.
- `evidence/`: local screenshots and a short smoke-test recording (gitignored).

The demo is time-limited and is not the licensed instance or benchmark world.
The separate demo runner enforces `--demo`; it does not bypass ownership checks.

## Rebuild reference

The VM already exists. These commands are for a deliberate rebuild on a new
machine, not for ordinary startup. Install Lima with Homebrew first, then:

```sh
limactl start --name=minecraft-lab tools/minecraft-vm/minecraft-vm.yaml
limactl copy tools/minecraft-vm/provision.sh minecraft-lab:/tmp/provision.sh
limactl shell minecraft-lab bash /tmp/provision.sh
```

Copy `control.py` to `~/minecraft-lab/control.py` in the guest. Use Prism's
instance wizard to add vanilla 26.3, choose Java 25, 512–4096 MiB memory and
854×480 resolution. A fresh rebuild also needs Microsoft login. The YAML's
Ubuntu image alias follows Lima's upstream image; for a published benchmark,
archive the exact VM snapshot/package versions rather than treating this
recipe as bit-for-bit reproducible.

Sources: [Lima VZ](https://lima-vm.io/docs/config/vmtype/vz/),
[Prism Java settings](https://prismlauncher.org/wiki/help-pages/java-settings/),
[Prism instance creation](https://prismlauncher.org/wiki/getting-started/create-instance/).
