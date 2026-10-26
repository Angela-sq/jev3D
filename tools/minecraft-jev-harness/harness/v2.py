"""v2: after v1 on the dev fights (4/10). What v1 lost and what changed:
  - pillager, witch, spider: the mob stood 2-3 blocks up (terraces at site B, a bush at site C); `approach` never
    jumped, so the player stood still below it for the whole fight. Now the chase moves sprint, and the body jumps
    when the mob is higher or the player stops moving forward.
  - stray, skeleton: two early hits, then the archer backed off and walking never caught up. Now chases sprint and
    sprint-jump when far; `zigzag_chase` steps left and right on the way in to spoil the aim.
  - creeper: two hits, then it exploded while the player kept striking. A creeper swells for 1.5 s once you are within
    3 blocks and only stops when you are 7+ blocks away. Now the state says how long it has been close, `flee` sprints
    away, and a reflex forces `flee` once it has been close for 0.6 s.
  - Jev picked `strike` out of reach and `approach` in reach. Now only the moves that fit the distance are offered:
    chase moves when far, fight moves in reach (all fight moves hit whenever the sword is ready and the mob is in reach).
  - The text adds how the mob fights, height, being stuck, and incoming arrows."""
import time
from harness.common import base_view,player_speed

INTERVAL=0.2
QUESTION='Which move gives the player the best chance to kill the mob without dying?'
RANGED={'skeleton','stray','pillager','witch'}
NOTES={
    'zombie':'Zombies walk at you and hit hard up close.','husk':'Husks walk at you, hit hard and make you hungry.',
    'skeleton':'Skeletons shoot arrows and back away when you come close.','stray':'Strays shoot slowing arrows and back away when you come close.',
    'spider':'Spiders are fast, leap at you and climb walls.','cave_spider':'Cave spiders are small, fast and poisonous.',
    'creeper':'Creepers explode 1.5 seconds after you come within 3 blocks; getting 7+ blocks away stops the fuse.',
    'witch':'Witches throw harmful potions from range and drink healing potions.','pillager':'Pillagers shoot crossbow bolts from range.',
    'vindicator':'Vindicators run at you and hit very hard with an axe.'}
TACTICS={
    'chase':dict(keys=['w'],sprint=True,chase=True,strike=True),
    'zigzag_chase':dict(keys=['w'],sprint=True,chase=True,zigzag=True,strike=True),
    'go_around_left':dict(keys=['w','a'],jump=True,strike=True),
    'go_around_right':dict(keys=['w','d'],jump=True,strike=True),
    'flee':dict(keys=['w'],sprint=True,aim_away=True,jump=True),
    'fight':dict(strike=True,close_in=True),
    'crit':dict(strike=True,close_in=True,crit=True),
    'circle_left':dict(keys=['a'],strike=True),
    'circle_right':dict(keys=['d'],strike=True),
    'back_off':dict(keys=['s']),
    'shield':dict(shield=True),
}
MOVES={
    'chase':'Sprint straight at the mob, jumping up steps; hits it as soon as it is in reach.',
    'zigzag_chase':'Sprint at the mob while stepping left and right, so arrows and potions miss; hits it in reach.',
    'go_around_left':'Walk forward-left around an obstacle, jumping.','go_around_right':'Walk forward-right around an obstacle, jumping.',
    'flee':'Turn and sprint away from the mob.',
    'fight':'Stand and swing the sword each time it is fully charged.',
    'crit':'Jump and swing while falling: a critical hit does 50% more damage but is slower.',
    'circle_left':'Circle left around the mob while swinging, to dodge its attacks.',
    'circle_right':'Circle right around the mob while swinging, to dodge its attacks.',
    'back_off':'Step back out of the mob\'s reach.',
    'shield':'Raise the shield: blocks arrows and hits from the front, but you cannot attack.',
}

def view(s,g,body,hits,mem,history):
    v=base_view(s,g,body,hits,mem,history);now=time.monotonic()
    v['speed']=player_speed(history)
    moving=mem['last'] in ('chase','zigzag_chase','go_around_left','go_around_right')
    mem['stuck_since']=(mem.get('stuck_since') or now) if moving and v['speed']<1.0 and v['hdist']>3 else None
    v['stuck_s']=now-mem['stuck_since'] if mem['stuck_since'] else 0.0
    if v['mob']=='creeper':
        if v['hdist']>7:mem['fuse_since']=None
        elif v['hdist']<=3.2 and not mem.get('fuse_since'):mem['fuse_since']=now
        v['fuse_s']=now-mem['fuse_since'] if mem.get('fuse_since') else 0.0
    return v

def options(v):
    if v['mob']=='creeper' and v.get('fuse_s',0)>=0.6:return {'flee':MOVES['flee']}
    if v['reach']<=3.2:
        names=['fight','crit','circle_left','circle_right','back_off']+(['flee'] if v['mob']=='creeper' else [])
    else:
        names=['chase','zigzag_chase']+(['go_around_left','go_around_right'] if v['stuck_s']>=0.8 else [])+(['shield'] if v['mob'] in RANGED else [])
        if v['mob']=='creeper' and v.get('fuse_s',0)>0:names=['flee','chase']
    return {k:MOVES[k] for k in names}

def describe(v):
    m=v['mob'];side='straight ahead' if abs(v['yaw_err'])<10 else f"{abs(v['yaw_err']):.0f} degrees to your {'right' if v['yaw_err']>0 else 'left'}"
    move='coming toward you' if v['closing']>.3 else 'moving away from you' if v['closing']<-.3 else 'keeping its distance'
    height='level with you' if abs(v['dy'])<.6 else f"{abs(v['dy']):.0f} blocks {'above' if v['dy']>0 else 'below'} you"
    lines=[f"Minecraft fight. You have an iron sword (6 damage, recharges in 0.6 s), a shield and iron armor. Goal: kill the {m} within 90 seconds without dying.",
           NOTES[m],
           f"The {m} is {v['hdist']:.1f} blocks away ({'IN REACH' if v['reach']<=3 else 'out of reach; reach is 3 blocks'}), {side}, {height}, {move} ({abs(v['closing']):.1f} blocks/s).",
           f"Your health: {v['php']:.0f}/20. The {m}'s health: {v['mhp']:.0f}/{v['mhp_max']} (about {max(1,round(v['mhp']/6+.49))} more hits).",
           f"Last 3 seconds: you hit it {v['hits_dealt_3s']} times; it hit you {v['hits_taken_3s']} times."]
    if v['stuck_s']>=0.8:lines.append(f"You are stuck: you have not moved for {v['stuck_s']:.1f} s while trying to get closer. Go around.")
    if v['arrows']:lines.append('An arrow or bolt is flying near you.')
    if m=='creeper' and v.get('fuse_s',0)>0:lines.append(f"The creeper's fuse has been burning for {v['fuse_s']:.1f} of 1.5 seconds. Get 7+ blocks away.")
    lines.append(f"Fight time: {v['t']:.0f} of 90 seconds. Your last move: {v['last'] or 'none'}.")
    return '\n'.join(lines)

def adjust(tac,s,g,body):
    """Reflexes, every 50 ms: jump on a chase when stalled or when the mob is higher (or far, to sprint-jump);
    zigzag; turn away to flee; crits only swing while falling; close in when the mob is just out of reach."""
    speed=player_speed(list(body.reader.history),4)
    if tac.get('chase') and (g['dy']>=.6 or speed<2.5 or g['hdist']>6):tac['jump']=True
    if tac.get('zigzag') and g['hdist']>3.5:tac['keys']=list(tac['keys'])+[('a' if int(time.monotonic()/.6)%2 else 'd')]
    if tac.get('close_in') and g['reach']>2.6:tac['keys']=list(tac.get('keys',()))+['w']
    if tac.get('crit'):
        tac['jump']=True
        if s['pground']:tac['strike']=False
    if tac.get('aim_away'):tac['aim_yaw_offset']=180
    if g['dy']>=.6 and speed<1 and tac.get('keys') and 'w' in tac['keys']:tac['jump']=True
    return tac
