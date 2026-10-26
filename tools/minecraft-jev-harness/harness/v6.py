"""v6: after v5 on the dev fights (8/10). What v5 lost and what changed:
  - pillager: it stood on top of the bush at site C, 2 blocks up and 1.8 blocks away; the aim was on it, but 131 swings
    did nothing (the leaves take the hit). Now the view counts swings in a row that did no damage; after 3, the state
    says the hits are blocked and only moving options are offered (climb at it, go around, back off to lure it out).
  - creeper: it jumped down its ledge and closed faster than the guard stepped back (the state is late); two pokes
    missed and the fuse lit. Now the guard steps back from 3.5 blocks (centre, 3D), and while the creeper is above on a
    ledge the player keeps 5 blocks away until it comes down."""
import time
from harness.v5 import INTERVAL,QUESTION,TACTICS as V5_TACTICS,MOVES as V5_MOVES,view as v5_view,options as v5_options,adjust as v5_adjust
from harness.v4 import describe as v4_describe

TACTICS={**V5_TACTICS,'climb':dict(keys=['w'],jump=True,strike=True)}
MOVES={**V5_MOVES,'climb':'Walk and jump straight at the mob to climb up to it; hits it when the way is clear.'}

def view(s,g,body,hits,mem,history):
    v=v5_view(s,g,body,hits,mem,history)
    # swings since the last damage dealt (a swing that lands shows up as a PVE_HIT within ~0.3 s)
    last_hit=(time.monotonic()-v['since_dealt']) if v['since_dealt'] is not None else 0
    mem.setdefault('swings',[]);mem['swings']=[t for t in mem['swings'] if t>last_hit]
    if body.last_click>last_hit+0.3 and body.last_click not in mem['swings'] and time.monotonic()-body.last_click>0.3:mem['swings'].append(body.last_click)
    v['missed']=len(mem['swings'])
    return v

def options(v):
    if v['missed']>=3 and v['mob']!='creeper':return {k:MOVES[k] for k in ['climb','go_around_left','go_around_right','back_off']}
    return v5_options(v)

def describe(v):
    text=v4_describe(v)
    if v['missed']>=3 and v['mob']!='creeper':
        text+=f"\nYour last {v['missed']} swings did no damage: something (leaves, a block) is between you and the {v['mob']}. Move to get a clear swing."
    return text

def adjust(tac,s,g,body):
    tac=v5_adjust(tac,s,g,body)
    if s['mob']=='creeper' and (g['dist3']<3.5 or (g['dy']>.9 and g['dist3']<5)):tac.update(keys=['s'],sprint=False,jump=False,shield=False)
    return tac
