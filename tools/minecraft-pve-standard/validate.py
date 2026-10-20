#!/usr/bin/env python3
"""Evaluator validation without any model: setup of every mob at every site, and forced end paths.

Writes OUT/validation/: one screenshot per mob and site, plus validation.json.
"""
import json,re,subprocess,sys,time
from config import OUT,VM,SITES
from core import MOBS,parse_end
LOG='.local/share/PrismLauncher/instances/26.3/minecraft/logs/latest.log'
V=OUT/'validation';V.mkdir(exist_ok=True)
def sh(cmd):return subprocess.run(['limactl','shell',VM,'bash','-c',cmd],capture_output=True,text=True,check=True).stdout
def command(c):subprocess.run(['limactl','shell',VM,'python3','minecraft-lab/pve-standard-tools/command.py',c],check=True)
def log_size():return int(sh(f'stat -c %s ~/{LOG}'))
def log_since(offset):return sh(f'tail -c +{offset+1} ~/{LOG}')
def capture(path):
    sh('DISPLAY=:99 scrot --overwrite -a 212,120,854,480 /tmp/v.png')
    subprocess.run(['limactl','copy',VM+':/tmp/v.png',str(path)],check=True)
def wait_end(offset,trial_id,seconds):
    for _ in range(seconds*4):
        for line in log_since(offset).splitlines():
            e=parse_end(line,trial_id)
            if e:return e
        time.sleep(.25)
    return None
def setup(mob,site):
    i=MOBS.index(mob);j=[s['site'] for s in SITES].index(site);n=-(100+10*i+j)
    offset=log_size();command(f'function pve:validate/{mob}_{site.lower()}');time.sleep(1.5)
    command('function pve:test/inspect');time.sleep(1)
    text=log_since(offset)
    inspect=[l.split('[CHAT] ',1)[1] for l in text.splitlines() if '[CHAT] PVE_INSPECT|' in l or '[CHAT] PVE_COUNT|' in l or '[CHAT] PVE_OTHERS|' in l]
    capture(V/f'{mob}_{site.lower()}.png')
    return n,offset,inspect
def forced(mob,site,test,expect,pre=None,wait=20):
    n,offset,inspect=setup(mob,site)
    if pre:command(f'function pve:test/{pre}')
    time.sleep(5.5)   # countdown ends, fight begins
    if test:command(f'function pve:test/{test}')
    e=wait_end(offset,n,wait)
    return {'mob':mob,'site':site,'test':test or 'natural','pre':pre,'expect':expect,'got':e and e['outcome'],'event':e,'inspect':inspect,'ok':bool(e) and e['outcome']==expect}
def main():
    only=sys.argv[1:]
    results=[]
    plan=[]
    tests=[('win','win'),('lost','target_lost'),('die','death')]
    for i,mob in enumerate(MOBS):
        for j,s in enumerate(SITES):
            test,expect=tests[(i+j)%3];plan.append((mob,s['site'],test,expect,None,20))
    plan+=[('zombie','A','win_and_die','death',None,20),('zombie','B','lost_and_die','death',None,20),
           ('creeper','A',None,'target_lost','invulnerable',60),('zombie','C',None,'timeout','invulnerable',110)]
    for p in plan:
        if only and p[0] not in only:continue
        r=forced(*p);results.append(r)
        print(json.dumps({k:r[k] for k in ['mob','site','test','expect','got','ok']}),flush=True)
        time.sleep(3)
    (V/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print('all ok' if all(r['ok'] for r in results) else 'FAILURES')
if __name__=='__main__':main()
