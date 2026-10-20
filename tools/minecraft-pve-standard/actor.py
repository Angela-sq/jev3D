#!/usr/bin/env python3
"""Actor-facing host transport. Never supplies game state or combat advice."""
import subprocess,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from config import OUT,VM,GUEST_TOOLS
start=time.time_ns()
r=subprocess.run(['limactl','shell',VM,'python3',GUEST_TOOLS+'/guest_trial.py',*sys.argv[1:]],capture_output=True,text=True,check=True)
d=json.loads(r.stdout.strip());remote=Path(d['image']);trial=remote.parent.name
local=OUT/'trials'/trial/remote.name;local.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['limactl','copy',VM+':'+str(remote),str(local)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
d['image']=str(local)
with (local.parent/'transport.jsonl').open('a') as f:f.write(json.dumps({'args':sys.argv[1:],'request_ns':start,'response_ns':time.time_ns(),'image':local.name})+'\n')
print(json.dumps(d))
