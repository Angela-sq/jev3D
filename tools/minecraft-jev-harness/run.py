#!/usr/bin/env python3
"""Host runner for the Jev text-harness runs.
  python3 run.py deploy                  build and load the datapack; copy player, harnesses and key to the guest
  python3 run.py run HARNESS SET [NAME]  run every fight of SET (smoke, dev, eval) with harness HARNESS (e.g. v1)
  python3 run.py summary
  python3 run.py release TAG             move videos and screenshots to GitHub release TAG, then delete local copies
Every fight gets a new trial ID; every attempt is kept, none is retried. Stops on a Jev key/credit error,
3 failures in a row, or when the token budget is spent."""
import csv,json,statistics,subprocess,sys,time
from collections import Counter
from config import OUT,TOOLS,VM,GUEST_TOOLS,WORLD,BUDGET_TOKENS,STANDARD,guest_trial_dir
def sh(cmd,check=True):return subprocess.run(['limactl','shell',VM,'bash','-c',cmd],capture_output=True,text=True,check=check)
def jsonl(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()] if p.exists() else []
RUNS=OUT/'runs.json'
def runs():return json.loads(RUNS.read_text()) if RUNS.exists() else []

def sets():
    """smoke: one zombie fight. dev: the first standard fight of each mob (10). eval: the 50 standard fights, same order."""
    std=json.loads((STANDARD/'schedule.json').read_text())['trials']
    src=lambda t:200+t['trial_id'] if t['mob'] in ('spider','cave_spider') else t['trial_id']
    fights=[dict(mob=t['mob'],site=t['site'],repeat=t['repeat'],source=src(t),standard_trial=t['trial_id']) for t in std]
    dev=list({f['mob']:f for f in reversed(fights)}.values())[::-1]
    return {'smoke':[f for f in fights if f['mob']=='zombie'][:1],'dev':dev,'eval':fights}

def deploy():
    subprocess.run([sys.executable,'build_pack.py'],cwd=TOOLS,check=True)
    subprocess.run(f'COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -C "{OUT}" -czf /tmp/jevhpack.tgz datapack',shell=True,check=True)
    subprocess.run(f'COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata --exclude __pycache__ -C "{TOOLS}" -czf /tmp/jevhtools.tgz player.py guest_trial.py core.py command.py harness',shell=True,check=True)
    for f in ['jevhpack.tgz','jevhtools.tgz']:subprocess.run(['limactl','copy','/tmp/'+f,f'{VM}:/tmp/{f}'],check=True)
    sh(f'mkdir -p {GUEST_TOOLS} ~/.config/typesafe && chmod 700 ~/.config/typesafe && rm -rf {GUEST_TOOLS}/harness && tar -C {GUEST_TOOLS} -xzf /tmp/jevhtools.tgz')
    subprocess.run(['limactl','copy',str(__import__('pathlib').Path.home()/'.config/typesafe/api_key'),VM+':.config/typesafe/api_key'],check=True)
    sh(f'chmod 600 ~/.config/typesafe/api_key; W="$HOME/{WORLD}"; rm -rf "$W/datapacks/jevh" /tmp/jk; mkdir /tmp/jk; tar -C /tmp/jk -xzf /tmp/jevhpack.tgz; mv /tmp/jk/datapack "$W/datapacks/jevh"; find "$W/datapacks" -name "._*" -delete')
    sh(f'python3 {GUEST_TOOLS}/command.py reload; sleep 2; python3 {GUEST_TOOLS}/command.py \'datapack enable "file/jevh"\'; sleep 2')
    print('jevh loaded lines in log:',sh('grep -ac "JEVH pack loaded" ~/.local/share/PrismLauncher/instances/26.3/minecraft/logs/latest.log',check=False).stdout.strip())

def game_alive():return sh('pgrep -f "[j]ava.*minecraft" >/dev/null',check=False).returncode==0
def restart_game():
    subprocess.run([sys.executable,'open_world.py'],cwd=TOOLS.parent/'minecraft-pve-standard',check=True)
    sh(f'python3 {GUEST_TOOLS}/command.py \'datapack enable "file/jevh"\'; sleep 2')

def sync(n):
    local=OUT/'trials'/f'trial-{n:04d}';local.mkdir(parents=True,exist_ok=True)
    tar=subprocess.Popen(['limactl','shell',VM,'tar','-C',guest_trial_dir(n),'-cf','-','.'],stdout=subprocess.PIPE)
    subprocess.run(['tar','-C',str(local),'-xf','-'],stdin=tar.stdout,check=True)
    if tar.wait():raise RuntimeError('tar from guest failed')

def tokens_used():return sum(json.loads(p.read_text()).get('input_tokens',0) for p in OUT.glob('trials/*/jev.json'))

FIELDS=['trial_id','run','harness','mob','site','repeat','outcome','game_seconds','kills','health_remaining','damage_dealt_stat','damage_taken_stat','steps','asked','clicks','jev_latency_median_s','jev_errors','input_tokens','choice_counts']
def rows():
    out=[]
    for r in runs():
        for t in r['trials']:
            d=OUT/'trials'/f"trial-{t['trial_id']:04d}"
            if not (d/'result.json').exists():continue
            res=json.loads((d/'result.json').read_text());meta=json.loads((d/'jev.json').read_text()) if (d/'jev.json').exists() else {}
            steps=jsonl(d/'steps.jsonl');lat=[x['jev_latency_s'] for x in steps if x.get('jev_latency_s')]
            out.append(dict(trial_id=t['trial_id'],run=r['name'],harness=r['harness'],mob=t['mob'],site=t['site'],repeat=t['repeat'],outcome=res['outcome'],
                game_seconds=res.get('game_seconds',''),kills=res.get('kills',''),health_remaining=res.get('health_remaining',''),
                damage_dealt_stat=res.get('damage_dealt_stat',''),damage_taken_stat=res.get('damage_taken_stat',''),steps=len(steps),
                asked=meta.get('asked',''),clicks=meta.get('clicks',''),jev_latency_median_s=round(statistics.median(lat),3) if lat else '',
                jev_errors=meta.get('jev_errors',''),input_tokens=meta.get('input_tokens',''),choice_counts=json.dumps(dict(Counter(x.get('choice') for x in steps)))))
    return out
def summary():
    rs=rows();OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rs)
    def summ(g):return dict(fights=len(g),wins=sum(r['outcome']=='win' for r in g),outcomes=dict(Counter(r['outcome'] for r in g)),
                            wins_by_mob={m:f"{sum(r['outcome']=='win' for r in g if r['mob']==m)}/{sum(r['mob']==m for r in g)}" for m in dict.fromkeys(r['mob'] for r in g)})
    tok=tokens_used()
    out=dict(input_tokens=tok,cost_usd=round(tok*0.042/1e6,4),by_run={r['name']:dict(harness=r['harness'],set=r['set'],**summ([x for x in rs if x['run']==r['name']])) for r in runs()})
    (OUT/'summary.json').write_text(json.dumps(out,indent=2)+'\n');return out

def run(harness,setname,name=None):
    rs=runs();name=name or f'{harness}-{setname}'
    r=next((x for x in rs if x['name']==name),None)
    if r is None:
        start=max([t['trial_id'] for x in rs for t in x['trials']],default=0)+1
        r=dict(name=name,harness=harness,set=setname,trials=[dict(f,trial_id=start+i) for i,f in enumerate(sets()[setname])])
        rs.append(r);RUNS.parent.mkdir(parents=True,exist_ok=True);RUNS.write_text(json.dumps(rs,indent=1)+'\n')
    assert r['harness']==harness and r['set']==setname,'run name already used with another harness or set'
    fails=0
    for t in r['trials']:
        n=t['trial_id']
        if (OUT/'trials'/f'trial-{n:04d}').exists():continue   # every attempt is kept; none is retried
        if tokens_used()>BUDGET_TOKENS:sys.exit('stopping: token budget spent')
        if not game_alive():print('game not running; restarting',flush=True);restart_game()
        start=time.time()
        p=subprocess.run(['limactl','shell',VM,'python3',GUEST_TOOLS+'/player.py',str(n),str(t['source']),harness],capture_output=True,text=True,timeout=400)
        if sh(f'test -d {guest_trial_dir(n)}',check=False).returncode==0:sync(n)
        res=OUT/'trials'/f'trial-{n:04d}'/'result.json'
        outcome=json.loads(res.read_text())['outcome'] if res.exists() else 'missing'
        print(time.strftime('%H:%M:%S'),name,n,t['mob'],t['site'],outcome,p.stdout.strip(),p.stderr.strip()[-300:],f'{time.time()-start:.0f}s',flush=True)
        summary()
        if p.returncode==3:sys.exit(f'stopping: Jev refused the request on trial {n}')
        fails=fails+1 if p.returncode or outcome in ('technical','missing') else 0
        if fails>=3:sys.exit('stopping: 3 failed trials in a row')
        if p.returncode or outcome in ('technical','missing'):print('restarting game after failure',flush=True);restart_game()
        time.sleep(3)
    print(json.dumps(summary()['by_run'][name],indent=1))

def release(tag):
    """Move every finished run's videos and screenshots to the GitHub release TAG (one tar per run), check each
    upload's size, then delete those files on the Mac and in the guest."""
    import tempfile
    from pathlib import Path
    tmp=Path(tempfile.mkdtemp())
    if subprocess.run(['gh','release','view',tag],capture_output=True).returncode:
        subprocess.run(['gh','release','create',tag,'--title','Jev text harness — videos and screenshots','--notes',f'Videos and screenshots of {OUT.relative_to(TOOLS.parents[1])}, one tar per run.'],check=True)
    for r in runs():
        dirs=[OUT/'trials'/f"trial-{t['trial_id']:04d}" for t in r['trials']]
        media=sorted(str(f.relative_to(OUT)) for d in dirs if (d/'complete').exists() for f in [*d.glob('video.mp4'),*d.glob('*.png')])
        if not media:continue
        tar=tmp/f"{r['name']}.tar"
        subprocess.run(['tar','--no-xattrs','--no-mac-metadata','-C',str(OUT),'-cf',str(tar),*media],check=True,env={'COPYFILE_DISABLE':'1','PATH':'/usr/bin:/bin'})
        subprocess.run(['gh','release','upload',tag,str(tar),'--clobber'],check=True)
        sizes={a['name']:a['size'] for a in json.loads(subprocess.run(['gh','release','view',tag,'--json','assets'],capture_output=True,text=True,check=True).stdout)['assets']}
        if sizes.get(tar.name)!=tar.stat().st_size:sys.exit(f'upload size mismatch for {tar.name}; nothing deleted')
        for m in media:(OUT/m).unlink()
        guest=' '.join(f"{guest_trial_dir(t['trial_id'])}/{{video.mp4,*.png}}" for t in r['trials'])
        sh(f'rm -f {guest}',check=False);tar.unlink()
        print(r['name'],len(media),'files moved to release',tag,flush=True)

if __name__=='__main__':
    op=sys.argv[1]
    if op=='deploy':deploy()
    elif op=='release':release(sys.argv[2])
    elif op=='summary':print(json.dumps(summary(),indent=1))
    elif op=='run':run(*sys.argv[2:])
    else:sys.exit(__doc__)
