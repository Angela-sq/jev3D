"""Settings for Jev data runs. Fights reuse the standard PvE benchmark's setups."""
import subprocess
from functools import cache
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
OUT=REPO/'experiments/minecraft-jev-data-2026-10-23-v2'
STANDARD=REPO/'experiments/minecraft-pve-standard-2026-10-19'
VM='minecraft-lab'
GUEST_TOOLS='minecraft-lab/jev-data-tools'   # relative to the guest home
GUEST_TRIALS='minecraft-lab/jev-data-v2'
WORLD='.local/share/PrismLauncher/instances/26.3/minecraft/saves/Astra Natural PVE'
MODEL='jev-preview'
BUDGET_TOKENS=35_000_000   # about $1.47 at $0.042 per million input tokens

@cache
def guest_home():
    return subprocess.run(['limactl','shell',VM,'sh','-c','echo $HOME'],capture_output=True,text=True,check=True).stdout.strip()

def guest_trial_dir(n):
    return f'{guest_home()}/{GUEST_TRIALS}/trial-{n:03d}'
