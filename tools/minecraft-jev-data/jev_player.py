#!/usr/bin/env python3
"""Jev plays one trial in the guest: screenshot -> Jev picks an action -> the action is played -> repeat.
Every step is logged to steps.jsonl with Jev's answers and the damage dealt/taken before the next screenshot.
Exit 3 means Jev refused the key or credit (stop the whole run)."""
import base64,fcntl,json,random,re,sys,time,urllib.error,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import guest_trial as gt
from core import validate_action,parse_end

KEY=(Path.home()/'.config/typesafe/api_key').read_text().strip()
MODEL='jev-preview'
URL='https://api.typesafe.ai/v1/systemone'
GOAL='First-person Minecraft. The player holds an iron sword and a shield, wears iron armor, and must kill the one hostile mob nearby without dying.'
# name -> (rule Jev reads, inputs played). 100 px of mouse = 15 degrees.
ACTIONS={
    'forward':('The mob is near the screen centre but small or far away (more than 3 blocks): walk toward it.',[{'keys':['w'],'ms':400}]),
    'back':('The mob is very close and the player is low on health: back away.',[{'keys':['s'],'ms':400}]),
    'turn_left':('No mob is visible, or the mob is in the left part of the screen: turn left.',[{'dx':-100}]),
    'turn_right':('The mob is in the right part of the screen: turn right.',[{'dx':100}]),
    'attack':('The mob is under the crosshair AND very close, filling a large part of the screen: swing the sword.',[{'buttons':[1],'ms':80}]),
    'charge':('The mob is under the crosshair and 2 to 4 blocks away: step toward it and swing.',[{'keys':['w'],'ms':250},{'buttons':[1],'ms':80}]),
    'shield':('A skeleton, stray or pillager is aiming at the player, or a creeper is flashing nearby: raise the shield.',[{'buttons':[3],'ms':500}]),
}
GREEDY=lambda n:801<=n<=850
HIT=re.compile(r'\[CHAT\] PVE_HIT\|(-?\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\s*$')

class Fatal(Exception):pass

def ask(png,previous,rng):
    ref=f'img-{uuid.uuid4()}'
    opts=list(ACTIONS.items());rng.shuffle(opts)   # Jev leans toward the first option
    body={'model':MODEL,'state':{'screen':ref,'goal':GOAL,'previous_action':previous or 'none'},
          'assets':{ref:{'type':'image','format':'png','data_base64':base64.b64encode(png.read_bytes()).decode()}},
          'questions':{'action':{'type':'choice','instructions':'Which single action should the player take next to kill the mob in `screen` without dying?','criteria':{k:v[0] for k,v in opts}},
                       'mob_visible':{'type':'noul','instructions':'A hostile mob is visible in `screen`.'},
                       'mob':{'type':'box','instructions':'The hostile mob in `screen`.'}}}
    data=json.dumps(body).encode();errors=[]
    for attempt in range(3):
        req=urllib.request.Request(URL,data=data,headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json','TypeSafe-Danger-Zone-Images':'true'})
        t=time.perf_counter()
        try:
            with urllib.request.urlopen(req,timeout=10) as r:out=json.loads(r.read())
            out['latency_s']=round(time.perf_counter()-t,3);out['errors']=errors;out['order']=[k for k,_ in opts]
            return out
        except urllib.error.HTTPError as e:
            msg=e.read().decode(errors='replace')[:300]
            if e.code in (401,402,403):raise Fatal(f'HTTP {e.code}: {msg}')
            errors.append(f'HTTP {e.code}: {msg}')
        except Exception as e:errors.append(type(e).__name__+': '+str(e)[:200])
        time.sleep(0.5*(attempt+1))
    return {'errors':errors}

def play(d,name):
    event={'kind':'action','action':name,'primitives':ACTIONS[name][1],'start_ns':time.time_ns()}
    with (gt.ROOT/'input.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            for a in ACTIONS[name][1]:
                a=validate_action(a)
                if a['dx'] or a['dy']:gt.run('xdotool','mousemove_relative','--',str(a['dx']),str(a['dy']))
                if a['keys']:gt.run('xdotool','keydown',*a['keys'])
                for b in a['buttons']:gt.run('xdotool','mousedown',str(b))
                time.sleep(a['ms']/1000);gt.release()
        except BaseException as e:event['error']=type(e).__name__;raise
        finally:gt.release();event['end_ns']=time.time_ns();gt.append(d/'actions.jsonl',event)

class Log:
    def __init__(self,n,offset):self.n=n;self.f=gt.LOG.open();self.f.seek(offset);self.hits=[];self.end=None;self.started=False
    def drain(self):
        while line:=self.f.readline():
            if f'[CHAT] PVE_START|{self.n}' in line:self.started=True
            m=HIT.search(line)
            if m and int(m[1])==self.n:self.hits.append(dict(time_ns=time.time_ns(),ticks=int(m[2]),hp=int(m[3])/100,dealt=int(m[4]),taken=int(m[5])))
            self.end=self.end or parse_end(line,self.n)
    def take(self):h=self.hits;self.hits=[];return h

def main():
    n=int(sys.argv[1]);d=gt.ROOT/f'trial-{n:03d}';rng=random.Random(n)
    offset=gt.LOG.stat().st_size
    r=gt.subprocess.run([sys.executable,gt.__file__,'begin',str(n)],capture_output=True,text=True)
    if r.returncode:print(r.stderr,file=sys.stderr);sys.exit(1)
    log=Log(n,offset);deadline=time.monotonic()+10
    while not log.started and not log.end and time.monotonic()<deadline:log.drain();time.sleep(.05)   # wait out the 5 s countdown
    meta={'model':MODEL,'policy':'top choice' if GREEDY(n) else 'sample','actions':{k:v[0] for k,v in ACTIONS.items()},'started_ns':time.time_ns(),'input_tokens':0,'steps':0,'jev_errors':0,'fatal':None}
    previous=None;step=None;stop=time.monotonic()+125
    try:
        while time.monotonic()<stop:
            log.drain()
            if step:step['hits']=log.take();gt.append(d/'steps.jsonl',step)
            if log.end or (d/'result.json').exists():step=None;break
            obs=Path(gt.capture(d)['image'])
            out=ask(obs,previous,rng);answers=out.get('answers')
            step={'step':meta['steps'],'obs':obs.name,'time_ns':time.time_ns(),'previous_action':previous,'jev_latency_s':out.get('latency_s'),
                  'jev_errors':out.get('errors'),'option_order':out.get('order'),'input_tokens':out.get('usage',{}).get('input_tokens',0)}
            meta['steps']+=1;meta['input_tokens']+=step['input_tokens']
            if not answers:
                meta['jev_errors']+=1;step['action']=None;time.sleep(.2);continue
            probs=answers['action']['probabilities'];names=sorted(probs)
            step.update(jev_choice=answers['action']['choice'],probabilities=probs,confidence=answers['action'].get('confidence'),
                        mob_visible=answers['mob_visible']['noul'],mob_box=answers['mob'].get('box'),mob_box_confidence=answers['mob'].get('confidence'))
            # batch4 (801-850) plays Jev's top choice; all other fights sample from Jev's probabilities
            step['action']=step['jev_choice'] if GREEDY(n) else rng.choices(names,weights=[probs[k] for k in names])[0]
            play(d,step['action']);previous=step['action']
    except Fatal as e:meta['fatal']=str(e)
    finally:
        gt.release()
        if step:step['hits']=log.take();gt.append(d/'steps.jsonl',step)
    for _ in range(300):
        if (d/'complete').exists():break
        time.sleep(.1)
    meta['ended_ns']=time.time_ns();(d/'jev.json').write_text(json.dumps(meta,indent=2))
    if meta['fatal']:print(meta['fatal'],file=sys.stderr);sys.exit(3)
    print(json.dumps({k:meta[k] for k in ['steps','input_tokens','jev_errors']}))
if __name__=='__main__':main()
