"""Shared validation and evaluator-event parsing; no game policy."""
import re
KEYS={'w','a','s','d','space','Shift_L','Control_L','1'}
def validate_action(a):
    if not isinstance(a,dict) or set(a)-{'keys','buttons','ms','dx','dy'}:raise ValueError('Unknown action fields')
    out={'keys':a.get('keys',[]),'buttons':a.get('buttons',[]),'ms':a.get('ms',0),'dx':a.get('dx',0),'dy':a.get('dy',0)}
    if not isinstance(out['keys'],list) or any(k not in KEYS for k in out['keys']):raise ValueError('Forbidden key')
    if not isinstance(out['buttons'],list) or any(type(b) is not int or b not in [1,3] for b in out['buttons']):raise ValueError('Forbidden button')
    for k,lo,hi in [('ms',0,1000),('dx',-300,300),('dy',-300,300)]:
        if type(out[k]) is not int or not lo<=out[k]<=hi:raise ValueError('Out of range: '+k)
    return out

def parse_end(line,trial_id):
    m=re.search(r'\[CHAT\] PVE_END\|(-?\d+)\|(\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\|(\d+)\s*$',line)
    if not m:return None
    n,code,ticks,hp,kills,taken,dealt=map(int,m.groups())
    if n!=trial_id or code not in [1,2,3,4]:return None
    return dict(trial_id=n,outcome={1:'win',2:'death',3:'timeout',4:'technical'}[code],ticks=ticks,game_seconds=ticks/20,health_remaining=0 if code==2 else hp/100,health_readback=hp/100,kills=kills,damage_taken_stat=taken,damage_dealt_stat=dealt,event=line.strip())
