"""v3: after v2 on the dev fights (8/10). What v2 lost and what changed:
  - vindicator: a straight trade of hits (it hits for ~8.6); v2 died with the vindicator at 6/24 (v1 had won the same
    race by one hit). The sword reaches 3 blocks to the mob's hitbox, farther than a mob's own reach, so now a
    `spacing` move hits as soon as the sword is charged and steps back while it recharges.
  - creeper: v2 sprinted in to 2 blocks, which lit the fuse, and the forced turn-and-flee came too late. The fuse lights
    when the creeper's centre is within 3 blocks of yours, while the sword reaches about 3.3 blocks to its centre. Now
    creepers get `poke` (keep the centre 3.25+ blocks away, hit at the edge of reach) and `wait_for_it` (let it walk
    into reach) instead of chase/fight; the fuse is counted from 3.0 blocks.
  - the body strikes only within `reach` of the hitbox (2.9; 3.0 for `poke`)."""
from harness.v2 import INTERVAL,QUESTION,RANGED,NOTES,view as v2_view,describe as v2_describe,adjust as v2_adjust
from harness.v2 import TACTICS as V2_TACTICS,MOVES as V2_MOVES
import time

TACTICS={**V2_TACTICS,
    'spacing':dict(strike=True,spacing=2.4),
    'poke':dict(strike=True,spacing=3.25,reach=3.0,center=True),
    'wait_for_it':dict(strike=True,reach=3.0),
}
MOVES={**V2_MOVES,
    'spacing':'Hit the moment the sword is charged, then step back while it recharges, so the mob cannot reach you.',
    'poke':'Stay just outside the creeper\'s fuse range (3 blocks) and hit it at the edge of your reach; each hit knocks it back.',
    'wait_for_it':'Stand still facing the mob and hit it when it walks into reach.',
}

def view(s,g,body,hits,mem,history):
    v=v2_view(s,g,body,hits,mem,history)
    if v['mob']=='creeper':   # recount the fuse from 3.0 blocks (centre to centre)
        now=time.monotonic()
        if v['hdist']>7:mem['fuse3']=None
        elif v['hdist']<3.0 and not mem.get('fuse3'):mem['fuse3']=now
        v['fuse_s']=now-mem['fuse3'] if mem.get('fuse3') else 0.0
    return v

def options(v):
    if v['mob']=='creeper':
        if v['fuse_s']>=0.6:names=['flee']
        elif v['fuse_s']>0:names=['flee','poke']
        elif v['hdist']<=5:names=['poke','wait_for_it','back_off']
        else:names=['wait_for_it','poke','chase']
    elif v['reach']<=3.2:names=['spacing','fight','crit','circle_left','circle_right','back_off']
    else:
        names=['chase','zigzag_chase']+(['go_around_left','go_around_right'] if v['stuck_s']>=0.8 else [])+(['shield'] if v['mob'] in RANGED else [])
        if v['closing']>1 and v['hdist']<6:names.append('wait_for_it')
    return {k:MOVES[k] for k in names}

def describe(v):return v2_describe(v)

def adjust(tac,s,g,body):
    """v2's reflexes, plus spacing: back off while the sword recharges if the mob is closer than `spacing`
    (centre distance for creepers), step in when it is out of reach and the sword is charged."""
    tac=v2_adjust(tac,s,g,body)
    if 'spacing' in tac:
        d=g['hdist'] if tac.get('center') else g['reach'];ready=body.cooldown()>=.95
        if d<tac['spacing'] and not (ready and g['reach']<=tac.get('reach',2.9) and not tac.get('center')):tac['keys']=['s']
        elif g['reach']>tac.get('reach',2.9) and (ready or d>tac['spacing']+1):tac['keys']=['w']
        else:tac['keys']=[]
    return tac
