#!/usr/bin/env python3
"""Host runner: python3 run.py deploy | summary | GROUP... (pilot, batch, batch2, batch3, batch4).
Runs each scheduled fight once (Jev in the guest), copies its evidence home, and rebuilds results.csv/summary.json.
Stops on a Jev key/credit error or when the token budget is spent."""
import csv,json,statistics,subprocess,sys,time
from collections import Counter
from config import OUT,TOOLS,VM,GUEST_TOOLS,WORLD,BUDGET_TOKENS,guest_trial_dir
sys.path.insert(0,str(TOOLS.parent/'minecraft-pve-standard'))
def sh(cmd,check=True):return subprocess.run(['limactl','shell',VM,'bash','-c',cmd],capture_output=True,text=True,check=check)
def jsonl(p):return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []

def deploy():
    subprocess.run([sys.executable,'build_pack.py'],cwd=TOOLS,check=True)
    subprocess.run(f'COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -C "{OUT}" -czf /tmp/jevpack.tgz datapack',shell=True,check=True)
    subprocess.run(['limactl','copy','/tmp/jevpack.tgz',VM+':/tmp/jevpack.tgz'],check=True)
    sh(f'mkdir -p {GUEST_TOOLS} ~/.config/typesafe && chmod 700 ~/.config/typesafe')
    for f in ['guest_trial.py','jev_player.py','core.py','command.py']:subprocess.run(['limactl','copy',str(TOOLS/f),f'{VM}:{GUEST_TOOLS}/{f}'],check=True)
    subprocess.run(['limactl','copy',str(__import__('pathlib').Path.home()/'.config/typesafe/api_key'),VM+':.config/typesafe/api_key'],check=True)
    sh(f'chmod 600 ~/.config/typesafe/api_key; W="$HOME/{WORLD}"; rm -rf "$W/datapacks/jevdata" /tmp/jk; mkdir /tmp/jk; tar -C /tmp/jk -xzf /tmp/jevpack.tgz; mv /tmp/jk/datapack "$W/datapacks/jevdata"; find "$W/datapacks" -name "._*" -delete')
    sh(f'python3 {GUEST_TOOLS}/command.py reload; sleep 2; python3 {GUEST_TOOLS}/command.py \'datapack enable "file/jevdata"\'; sleep 2')
    log=sh('grep -ac "JEV data pack loaded" ~/.local/share/PrismLauncher/instances/26.3/minecraft/logs/latest.log',check=False).stdout.strip()
    print('jevdata loaded lines in log:',log)

def game_alive():return sh('pgrep -f "[j]ava.*minecraft" >/dev/null',check=False).returncode==0
def restart_game():
    subprocess.run([sys.executable,'open_world.py'],cwd=TOOLS.parent/'minecraft-pve-standard',check=True)
    sh(f'python3 {GUEST_TOOLS}/command.py \'datapack enable "file/jevdata"\'; sleep 2')

def sync(n):
    local=OUT/'trials'/f'trial-{n:03d}';local.mkdir(parents=True,exist_ok=True)
    tar=subprocess.Popen(['limactl','shell',VM,'tar','-C',guest_trial_dir(n),'-cf','-','.'],stdout=subprocess.PIPE)
    subprocess.run(['tar','-C',str(local),'-xf','-'],stdin=tar.stdout,check=True)
    if tar.wait():raise RuntimeError('tar from guest failed')

def tokens_used():return sum(json.loads(p.read_text()).get('input_tokens',0) for p in OUT.glob('trials/*/jev.json'))

FIELDS=['trial_id','group','mob','site','repeat','outcome','game_seconds','kills','health_remaining','damage_dealt_stat','damage_taken_stat','steps','steps_per_second','jev_latency_median_s','jev_errors','input_tokens','action_counts','video','steps_log']
def rows():
    s=json.loads((OUT/'schedule.json').read_text());out=[]
    for group in s:
        for t in s[group]:
            d=OUT/'trials'/f"trial-{t['trial_id']:03d}"
            if not (d/'result.json').exists():continue
            r=json.loads((d/'result.json').read_text());meta=json.loads((d/'jev.json').read_text()) if (d/'jev.json').exists() else {}
            steps=jsonl(d/'steps.jsonl');lat=[x['jev_latency_s'] for x in steps if x.get('jev_latency_s')]
            out.append(dict(trial_id=t['trial_id'],group=group,mob=t['mob'],site=t['site'],repeat=t['repeat'],outcome=r['outcome'],game_seconds=r.get('game_seconds',''),
                kills=r.get('kills',''),health_remaining=r.get('health_remaining',''),damage_dealt_stat=r.get('damage_dealt_stat',''),damage_taken_stat=r.get('damage_taken_stat',''),
                steps=len(steps),steps_per_second=round(len(steps)/r['game_seconds'],2) if r.get('game_seconds') else '',
                jev_latency_median_s=round(statistics.median(lat),3) if lat else '',jev_errors=meta.get('jev_errors',''),input_tokens=meta.get('input_tokens',''),
                action_counts=json.dumps(dict(Counter(x.get('action') for x in steps))),video=f'trials/trial-{t["trial_id"]:03d}/video.mp4',steps_log=f'trials/trial-{t["trial_id"]:03d}/steps.jsonl'))
    return out
def summary():
    rs=rows()
    with (OUT/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rs)
    def summ(g):
        return dict(fights=len(g),outcomes=dict(Counter(r['outcome'] for r in g)),wins=sum(r['outcome']=='win' for r in g),
                    fights_with_damage_dealt=sum(int(r['damage_dealt_stat'] or 0)>0 for r in g),steps=sum(r['steps'] for r in g))
    tok=tokens_used()
    out=dict(input_tokens=tok,cost_usd=round(tok*0.042/1e6,4),
             by_group={g:summ([r for r in rs if r['group']==g]) for g in dict.fromkeys(r['group'] for r in rs)},
             batches_all=summ([r for r in rs if r['group']!='pilot']),
             batches_by_mob={m:summ([r for r in rs if r['group']!='pilot' and r['mob']==m]) for m in sorted({r['mob'] for r in rs if r['group']!='pilot'})})
    (OUT/'summary.json').write_text(json.dumps(out,indent=2)+'\n');return out

def run(group):
    s=json.loads((OUT/'schedule.json').read_text());fails=0
    for t in s[group]:
        n=t['trial_id']
        if (OUT/'trials'/f'trial-{n:03d}').exists():continue   # every attempt is kept; none is retried
        if tokens_used()>BUDGET_TOKENS:sys.exit('stopping: token budget spent')
        if not game_alive():print('game not running; restarting',flush=True);restart_game()
        start=time.time()
        r=subprocess.run(['limactl','shell',VM,'python3',GUEST_TOOLS+'/jev_player.py',str(n)],capture_output=True,text=True,timeout=400)
        if sh(f'test -d {guest_trial_dir(n)}',check=False).returncode==0:sync(n)
        res=OUT/'trials'/f'trial-{n:03d}'/'result.json'
        outcome=json.loads(res.read_text())['outcome'] if res.exists() else 'missing'
        print(time.strftime('%H:%M:%S'),n,t['mob'],t['site'],outcome,r.stdout.strip(),r.stderr.strip()[-300:],f'{time.time()-start:.0f}s',flush=True)
        summary()
        if r.returncode==3:sys.exit(f'stopping: Jev refused the request on trial {n}')
        fails=fails+1 if r.returncode or outcome in ('technical','missing') else 0
        if fails>=3:sys.exit('stopping: 3 failed trials in a row')
        if r.returncode or outcome in ('technical','missing'):print('restarting game after failure',flush=True);restart_game()
        time.sleep(3)

if __name__=='__main__':
    op=sys.argv[1]
    if op=='deploy':deploy()
    elif op=='summary':print(json.dumps(summary(),indent=1))
    else:
        for group in sys.argv[1:]:run(group)
        print(json.dumps(summary(),indent=1))
