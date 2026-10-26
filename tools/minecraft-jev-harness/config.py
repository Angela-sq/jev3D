"""Settings for the Jev text-harness runs. Fights reuse the standard PvE benchmark's setups."""
import subprocess
from functools import cache
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
OUT=REPO/'experiments/minecraft-jev-harness-2026-10-26'
STANDARD=REPO/'experiments/minecraft-pve-standard-2026-10-19'
VM='minecraft-lab'
GUEST_TOOLS='minecraft-lab/jev-harness-tools'   # relative to the guest home
GUEST_TRIALS='minecraft-lab/jev-harness'
WORLD='.local/share/PrismLauncher/instances/26.3/minecraft/saves/Astra Natural PVE'
MODEL='jev-preview'   # same model as the screenshot Jev run
BUDGET_TOKENS=50_000_000   # about $2.10 at $0.042 per million input tokens

@cache
def guest_home():
    return subprocess.run(['limactl','shell',VM,'sh','-c','echo $HOME'],capture_output=True,text=True,check=True).stdout.strip()

def guest_trial_dir(n):
    return f'{guest_home()}/{GUEST_TRIALS}/trial-{n:04d}'
