#!/usr/bin/env python3
"""Actor-facing host transport. Never supplies game state or combat advice."""
import subprocess,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'experiments/minecraft-pve-2026-10-22-v3'
start=time.time_ns()
r=subprocess.run(['limactl','shell','minecraft-lab','python3','minecraft-lab/controller-v3-oct22/guest_trial.py',*sys.argv[1:]],capture_output=True,text=True,check=True)
d=json.loads(r.stdout.strip());remote=Path(d['image']);trial=remote.parent.name
local=ROOT/'trials'/trial/remote.name;local.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['limactl','copy','minecraft-lab:'+str(remote),str(local)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
d['image']=str(local)
with (local.parent/'transport.jsonl').open('a') as f:f.write(json.dumps({'args':sys.argv[1:],'request_ns':start,'response_ns':time.time_ns(),'image':local.name})+'\n')
print(json.dumps(d))
