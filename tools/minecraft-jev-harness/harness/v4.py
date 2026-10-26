"""v4: after v3 on the dev fights (7/10). What v3 lost and what changed:
  - skeleton: 31 swings, 3 hits. The body swung whenever the aim was within 20 degrees, but a skeleton 2.5 blocks away
    is only ~7 degrees wide, and every miss restarts the sword's recharge. Now the body swings only when the crosshair
    is on the hitbox, aims ahead of the mob along its velocity (the state is ~3 ticks late) and turns faster when far off.
  - witch: v3 backed off between hits (`spacing`) and the witch drank healing potions. Mobs that fight from range
    (skeleton, stray, pillager, witch) do not melee, so spacing only gives them time: in reach they now get only the
    pressing moves (fight, crit, circle).
  - creeper: the fuse is measured centre to centre in 3D (the creeper had come down a ledge: 3.0 blocks flat but 3.6
    in 3D, not yet lit), and v3's forced turn-and-flee walked the player into it. Now a creeper guard steps back
    whenever the creeper's centre is closer than 3.3 blocks (the sword still swings when it can land), there is no
    turning away, and with the fuse lit the player keeps poking and backing off."""
from harness.v3 import INTERVAL,QUESTION,RANGED,NOTES as V3_NOTES,TACTICS as V3_TACTICS,MOVES as V3_MOVES
from harness.v3 import view as v3_view,adjust as v3_adjust
from harness.v2 import describe as v2_describe
import time

NOTES={**V3_NOTES,'witch':'Witches throw harmful potions from range and drink a healing potion when hurt: keep hitting so she cannot heal.'}
TACTICS=V3_TACTICS
MOVES={**V3_MOVES,'back_off':'Step back out of the mob\'s reach (for a creeper: out of its fuse range) while still facing it.'}

def view(s,g,body,hits,mem,history):
    v=v3_view(s,g,body,hits,mem,history);v['dist3']=g['dist3']
    if v['mob']=='creeper':
        now=time.monotonic()
        if g['dist3']>7:mem['fuse3d']=None
        elif g['dist3']<3.0 and not mem.get('fuse3d'):mem['fuse3d']=now
        v['fuse_s']=now-mem['fuse3d'] if mem.get('fuse3d') else 0.0
    return v

def options(v):
    if v['mob']=='creeper':
        if v['fuse_s']>0:names=['poke','back_off']
        elif v['dist3']<=5:names=['poke','wait_for_it','back_off']
        else:names=['wait_for_it','poke']
    elif v['reach']<=3.2:
        names=['fight','crit','circle_left','circle_right'] if v['mob'] in RANGED else ['spacing','fight','crit','circle_left','circle_right','back_off']
    else:
        names=['chase','zigzag_chase']+(['go_around_left','go_around_right'] if v['stuck_s']>=0.8 else [])+(['shield'] if v['mob'] in RANGED else [])
        if v['closing']>1 and v['hdist']<6:names.append('wait_for_it')
    return {k:MOVES[k] for k in names}

def describe(v):
    text=v2_describe(v)
    if v['mob']=='witch':text=text.replace(V3_NOTES['witch'],NOTES['witch'])
    if v['mob']=='creeper':text=text.replace('Get 7+ blocks away.','Keep poking it away; never let it walk into you.')
    return text

def adjust(tac,s,g,body):
    """v3's reflexes with no turning away, aim ahead of the mob, swing only on target, and the creeper guard."""
    tac.pop('aim_away',None)
    if tac.get('center'):g=dict(g,hdist=g['dist3'])   # poke measures the creeper's centre in 3D
    tac=v3_adjust(tac,s,g,body)
    tac.update(lead=3,fast_aim=True,aim_gate=True)
    if s['mob']=='creeper' and g['dist3']<3.3:tac.update(keys=['s'],sprint=False,jump=False,shield=False)
    return tac
