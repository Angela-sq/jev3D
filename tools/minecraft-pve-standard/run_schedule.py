#!/usr/bin/env python3
"""Run the fixed schedule in order. Skips recorded trials; one rerun per technical failure."""
import json,subprocess,sys,time
from config import OUT,TOOLS
def outcome(n):
    p=OUT/'trials'/f'trial-{n:03d}'/'result.json'
    return json.loads(p.read_text())['outcome'] if p.exists() else None
def run(n):
    if (OUT/'trials'/f'trial-{n:03d}').exists():return outcome(n)
    r=subprocess.run([sys.executable,str(TOOLS/'run_trial.py'),str(n)])
    if r.returncode==3:sys.exit(f'stopping: infrastructure problem on trial {n}')
    if r.returncode:sys.exit(f'stopping: run_trial failed on trial {n}')
    time.sleep(3)
    return outcome(n)
def main():
    s=json.loads((OUT/'schedule.json').read_text())
    todo=[t for t in s['amendments'] if not t.get('rerun_of')] if sys.argv[1:]==['amendments'] else s['trials']
    for t in todo:
        if run(t['trial_id'])=='technical':run(100+t['trial_id'])
if __name__=='__main__':main()
