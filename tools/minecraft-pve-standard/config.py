"""Fixed benchmark settings shared by host-side tools."""
import subprocess
from functools import cache
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
OUT=REPO/'experiments/minecraft-pve-standard-2026-10-19'
VM='minecraft-lab'
GUEST_TOOLS='minecraft-lab/pve-standard-tools'   # relative to the guest home
GUEST_TRIALS='minecraft-lab/pve-standard'
MODEL='claude-fable-5-1'
EFFORT='medium'
REPEATS=5
SCHEDULE_SEED=20261019
SITES=[{'site':'A','x':240.5,'z':-240.5,'description':'grassland terrace'},
       {'site':'B','x':270.5,'z':-210.5,'description':'grassland slope'},
       {'site':'C','x':215.5,'z':-190.5,'description':'grassland edge'}]
CALIBRATION=[{'trial_id':901,'mob':'zombie','site':'A','repeat':0,'scored':False}]

@cache
def guest_home():
    return subprocess.run(['limactl','shell',VM,'sh','-c','echo $HOME'],capture_output=True,text=True,check=True).stdout.strip()

def guest_trial_dir(n):
    return f'{guest_home()}/{GUEST_TRIALS}/trial-{n:03d}'
