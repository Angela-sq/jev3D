#!/usr/bin/env python3
"""Jev plays one trial in the guest through a text harness (after MCJev): python3 player.py TRIAL SOURCE HARNESS.

Three threads:
  - reader: tails the game log; the jevh pack prints the state every tick (JH) and every damage change (PVE_HIT).
  - body: 20 times a second it holds the tactic's keys, aims at the mob and swings when the sword is ready and the
    mob is in reach. A harness may add reflexes (adjust()).
  - head: writes the fight as text (harness describe()), offers the moves that make sense now (options()), asks Jev
    one choice question, and gives the top choice to the body. When only one move makes sense, Jev is not asked.
Every decision goes to steps.jsonl. Exit 3 means Jev refused the key or credit (stop the whole run)."""
import ctypes,importlib,json,math,random,re,sys,threading,time,urllib.error,urllib.request
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import guest_trial as gt
from core import parse_end,MOBS

KEY=(Path.home()/'.config/typesafe/api_key').read_text().strip()
MODEL='jev-preview'
URL='https://api.typesafe.ai/v1/systemone'
NUM=re.compile(r'-?\d+(?:\.\d+)?(?:[eE]-?\d+)?')
HIT=re.compile(r'\[CHAT\] PVE_HIT\|(-?\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\s*$')
DEG_PER_PX=0.15   # default mouse sensitivity: 100 px = 15 degrees
COOLDOWN=0.625    # iron sword: attack speed 1.6
# mob hitbox (width, height)
SIZE={'zombie':(.6,1.95),'husk':(.6,1.95),'skeleton':(.6,1.99),'stray':(.6,1.99),'spider':(1.4,.9),'cave_spider':(.7,.5),
      'creeper':(.6,1.7),'witch':(.6,1.95),'pillager':(.6,1.95),'vindicator':(.6,1.95)}

class Fatal(Exception):pass

def nums(s):return [float(x) for x in NUM.findall(s)]

class Reader:
    """The latest game state, the damage events and the end of the fight, from the game log."""
    def __init__(self,n,offset):
        self.n=n;self.f=gt.LOG.open();self.f.seek(offset);self.state=None;self.hits=[];self.end=None;self.started=None
        self.lock=threading.Lock();self.history=deque(maxlen=60)
    def drain(self):
        while line:=self.f.readline():
            if f'[CHAT] PVE_START|{self.n}' in line:self.started=time.monotonic()
            if '[CHAT] JH|' in line:
                p=line.split('[CHAT] JH|',1)[1].rstrip('\n').split('|')
                if len(p)==14 and p[0]==str(self.n):self._state(p)
            m=HIT.search(line)
            if m and int(m[1])==self.n:
                with self.lock:self.hits.append(dict(t=time.monotonic(),ticks=int(m[2]),hp=int(m[3])/100,dealt=int(m[4]),taken=int(m[5])))
            self.end=self.end or parse_end(line,self.n)
    def _state(self,p):
        _,ticks,mob,ppos,prot,php,phurt,pground,mpos,mrot,mhp,mhurt,mmot,arrows=p
        s=dict(t=time.monotonic(),ticks=int(ticks),mob=MOBS[int(mob)],ppos=nums(ppos),prot=nums(prot),php=(nums(php) or [0])[0],
               phurt=(nums(phurt) or [0])[0],pground=pground.strip()=='1b',mpos=nums(mpos),mrot=nums(mrot),mhp=(nums(mhp) or [None])[0],
               mhurt=(nums(mhurt) or [0])[0],mmot=nums(mmot),arrows=int(arrows or 0))
        with self.lock:self.state=s;self.history.append(s)
    def run(self,stop):
        while not stop.is_set():self.drain();time.sleep(.01)

def wrap(a):return (a+180)%360-180

def geometry(s,lead=0):
    """Where the mob is from the player's eyes: angles to turn, the distance to its hitbox (reach is 3), the centre
    distance (what mobs measure, e.g. a creeper's fuse) and how far off the aim may be and still hit (yaw_tol,
    pitch_tol). `lead` moves the mob along its velocity by that many ticks (the state is a little late)."""
    if not s or len(s['mpos'])<3 or len(s['ppos'])<3:return None
    w,h=SIZE[s['mob']];(px,py,pz),(mx,my,mz)=s['ppos'],s['mpos'];ey=py+1.62
    if lead and len(s['mmot'])==3:mx,my,mz=mx+s['mmot'][0]*lead,my+max(0,s['mmot'][1])*lead,mz+s['mmot'][2]*lead
    dx,dz=mx-px,mz-pz;hd=math.hypot(dx,dz)
    yaw_err=wrap(math.degrees(math.atan2(-dx,dz))-s['prot'][0])
    pitch_err=-math.degrees(math.atan2(my+h*.6-ey,max(hd,.01)))-s['prot'][1]
    near=[min(max(e,lo),hi) for e,lo,hi in ((px,mx-w/2,mx+w/2),(ey,my,my+h),(pz,mz-w/2,mz+w/2))]
    reach=math.dist((px,ey,pz),near)
    return dict(yaw_err=yaw_err,pitch_err=pitch_err,hdist=hd,dy=my-py,reach=reach,dist3=math.dist((px,py,pz),(mx,my,mz)),
                yaw_tol=math.degrees(math.atan2(w/2,max(hd,.3))),pitch_tol=math.degrees(math.atan2(h*.4,max(hd,.3))))

class Body:
    """Keyboard and mouse through XTest; the 20 Hz reflex loop."""
    def __init__(self,reader,harness):
        self.x=ctypes.CDLL('libX11.so.6');self.xt=ctypes.CDLL('libXtst.so.6')
        self.x.XOpenDisplay.restype=ctypes.c_void_p;self.x.XStringToKeysym.restype=ctypes.c_ulong
        self.d=ctypes.c_void_p(self.x.XOpenDisplay(b':99'))
        self.reader,self.h=reader,harness;self.tactic=None;self.held=set();self.buttons=set()
        self.last_click=0.0;self.clicks=0;self.lock=threading.Lock();self.moves=deque(maxlen=40);self.click_log=[]
    def _code(self,k):return self.x.XKeysymToKeycode(self.d,ctypes.c_ulong(self.x.XStringToKeysym(k.encode())))
    def key(self,k,down):self.xt.XTestFakeKeyEvent(self.d,self._code(k),bool(down),0)
    def button(self,b,down):self.xt.XTestFakeButtonEvent(self.d,b,bool(down),0)
    def move(self,dx,dy):self.xt.XTestFakeRelativeMotionEvent(self.d,int(dx),int(dy),0);self.moves.append((time.monotonic(),int(dx),int(dy)))
    def unseen_turn(self,s,lag):
        """Degrees (yaw, pitch) of mouse moves the state cannot show yet: those sent after it was read minus `lag`."""
        sent=[(dx,dy) for t,dx,dy in self.moves if t>s['t']-lag]
        return sum(x for x,_ in sent)*DEG_PER_PX,sum(y for _,y in sent)*DEG_PER_PX
    def flush(self):self.x.XFlush(self.d)
    def cooldown(self):return min(1.0,(time.monotonic()-self.last_click)/COOLDOWN)
    def set_keys(self,keys,buttons):
        for k in self.held-keys:self.key(k,False)
        for k in keys-self.held:self.key(k,True)
        for b in self.buttons-buttons:self.button(b,False)
        for b in buttons-self.buttons:self.button(b,True)
        self.held,self.buttons=set(keys),set(buttons)
    def release(self):self.set_keys(set(),set());self.flush()
    def step(self):
        with self.reader.lock:s=self.reader.state
        g=geometry(s);tac=self.tactic
        if not tac or not g:self.release();return
        tac=dict(tac)
        if hasattr(self.h,'adjust'):tac=self.h.adjust(tac,s,g,self)
        keys=set(tac.get('keys',()))|({'Control_L'} if tac.get('sprint') else set())|({'space'} if tac.get('jump') else set())
        buttons={3} if tac.get('shield') else set()
        self.set_keys(keys,buttons)
        a=geometry(s,tac['lead']) if tac.get('lead') else g   # where to aim and whether a swing would land
        if tac.get('predict_aim'):   # correct for turns already sent but not yet in the state
            uy,up=self.unseen_turn(s,tac['predict_aim']);a=dict(a,yaw_err=wrap(a['yaw_err']-uy),pitch_err=a['pitch_err']-up)
        if tac.get('aim',True):
            gain=tac.get('aim_gain',.35)
            if tac.get('fast_aim') and abs(a['yaw_err'])>10:gain=.6
            off=tac.get('aim_yaw_offset',0)
            yaw_err=wrap(a['yaw_err']+off);pitch_err=-s['prot'][1] if off else a['pitch_err']   # looking away: level gaze
            dx=max(-90,min(90,yaw_err*gain/DEG_PER_PX));dy=max(-60,min(60,pitch_err*gain/DEG_PER_PX))
            if abs(dx)>=1 or abs(dy)>=1:self.move(dx,dy)
        on_target=abs(a['yaw_err'])<=a['yaw_tol']+1.5 and abs(a['pitch_err'])<=a['pitch_tol']+1.5 if tac.get('aim_gate') else abs(g['yaw_err'])<20
        if tac.get('strike') and not tac.get('shield') and g['reach']<=tac.get('reach',2.9) and on_target and self.cooldown()>=tac.get('charge',.95):
            self.button(1,True);self.flush();time.sleep(.02);self.button(1,False);self.last_click=time.monotonic();self.clicks+=1
            self.click_log.append(dict(ticks=s['ticks'],reach=round(g['reach'],2),yaw_err=round(a['yaw_err'],1),pitch_err=round(a['pitch_err'],1)))
        self.flush()
    def run(self,stop):
        while not stop.is_set():
            t=time.monotonic()
            try:self.step()
            except Exception as e:print('body error',repr(e),file=sys.stderr)
            time.sleep(max(0,.05-(time.monotonic()-t)))
        self.release()

def ask(text,opts,question,rng):
    order=list(opts);rng.shuffle(order)   # Jev leans toward the first option
    body={'model':MODEL,'state':text,'questions':{'move':{'type':'choice','instructions':question,'criteria':{k:opts[k] for k in order}}}}
    data=json.dumps(body).encode();errors=[]
    for attempt in range(3):
        req=urllib.request.Request(URL,data=data,headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'})
        t=time.perf_counter()
        try:
            with urllib.request.urlopen(req,timeout=5) as r:out=json.loads(r.read())
            out['latency_s']=round(time.perf_counter()-t,3);out['errors']=errors;out['order']=order
            return out
        except urllib.error.HTTPError as e:
            msg=e.read().decode(errors='replace')[:300]
            if e.code in (401,402,403):raise Fatal(f'HTTP {e.code}: {msg}')
            errors.append(f'HTTP {e.code}: {msg}')
        except Exception as e:errors.append(type(e).__name__+': '+str(e)[:200])
        time.sleep(.2*(attempt+1))
    return {'errors':errors,'order':order}

def main():
    n,source,spec=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
    hname,_,policy=spec.partition('+')   # e.g. v7+random: the v7 harness with a uniform random pick instead of Jev
    h=importlib.import_module(f'harness.{hname}');d=gt.ROOT/f'trial-{n:04d}';rng=random.Random(n)
    offset=gt.LOG.stat().st_size
    r=gt.subprocess.run([sys.executable,gt.__file__,'begin',str(n),str(source)],capture_output=True,text=True)
    if r.returncode:print(r.stderr,file=sys.stderr);sys.exit(1)
    reader=Reader(n,offset);stop=threading.Event()
    threading.Thread(target=reader.run,args=(stop,),daemon=True).start()
    deadline=time.monotonic()+10
    while not reader.started and not reader.end and time.monotonic()<deadline:time.sleep(.02)   # the 5 s countdown
    body=Body(reader,h);bt=threading.Thread(target=body.run,args=(stop,),daemon=True);bt.start()
    meta={'model':None if policy=='random' else MODEL,'harness':hname,'policy':policy or 'jev top choice','source':source,'started_ns':time.time_ns(),'input_tokens':0,'steps':0,'asked':0,'jev_errors':0,'fatal':None}
    mem={'last':None,'events':deque(maxlen=8),'seen_hits':0,'start':reader.started or time.monotonic()}
    end=time.monotonic()+125
    try:
        with (d/'steps.jsonl').open('a') as log:
            while time.monotonic()<end and not reader.end and not (d/'result.json').exists():
                t0=time.monotonic()
                with reader.lock:s=reader.state;hits=list(reader.hits)
                g=geometry(s)
                if not g:time.sleep(.02);continue
                v=h.view(s,g,body,hits,mem,list(reader.history))
                opts=h.options(v);text=h.describe(v)
                step={'step':meta['steps'],'ticks':s['ticks'],'view':{k:(round(x,3) if isinstance(x,float) else x) for k,x in v.items() if not isinstance(x,(list,dict,deque))},'options':list(opts)}
                if len(opts)==1:choice=next(iter(opts))
                elif policy=='random':choice=rng.choice(sorted(opts))
                else:
                    step['text']=text;out=ask(text,opts,h.QUESTION,rng);meta['asked']+=1
                    tok=out.get('usage',{}).get('input_tokens',0);meta['input_tokens']+=tok
                    step.update(jev_latency_s=out.get('latency_s'),jev_errors=out.get('errors'),option_order=out.get('order'),input_tokens=tok)
                    if 'answers' not in out:meta['jev_errors']+=1;choice=mem['last'] if mem['last'] in opts else next(iter(opts))
                    else:a=out['answers']['move'];choice=a['choice'];step.update(probabilities=a['probabilities'],confidence=a.get('confidence'))
                body.tactic=h.TACTICS[choice];mem['last']=choice;step['choice']=choice;step['clicks']=body.clicks
                meta['steps']+=1;log.write(json.dumps(step)+'\n');log.flush()
                time.sleep(max(0,h.INTERVAL-(time.monotonic()-t0)))
    except Fatal as e:meta['fatal']=str(e)
    finally:
        body.tactic=None;stop.set();bt.join(2);body.release();gt.release()
    for _ in range(300):
        if (d/'complete').exists():break
        time.sleep(.1)
    meta.update(ended_ns=time.time_ns(),clicks=body.clicks,click_log=body.click_log);(d/'jev.json').write_text(json.dumps(meta,indent=2))
    if meta['fatal']:print(meta['fatal'],file=sys.stderr);sys.exit(3)
    print(json.dumps({k:meta[k] for k in ['steps','asked','input_tokens','jev_errors','clicks']}))
if __name__=='__main__':main()
