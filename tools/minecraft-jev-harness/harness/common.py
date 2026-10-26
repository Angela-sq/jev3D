"""Facts every harness version can use, computed from the game state (never shown to Jev as-is)."""
import time

def damage_events(hits):
    """[(t, 'dealt'|'taken', amount)] from the PVE_HIT totals (amounts in tenths of a heart-point, as the stats)."""
    out,pd,pt=[],0,0
    for h in hits:
        if h['dealt']>pd:out.append((h['t'],'dealt',h['dealt']-pd))
        if h['taken']>pt:out.append((h['t'],'taken',h['taken']-pt))
        pd,pt=h['dealt'],h['taken']
    return out

def closing_speed(history,mob):
    """Blocks per second the mob is coming closer (negative: moving away), over the last ~0.5 s."""
    import math
    pts=[s for s in history if len(s['mpos'])==3 and len(s['ppos'])==3][-11:]
    if len(pts)<2 or pts[-1]['ticks']==pts[0]['ticks']:return 0.0
    d=lambda s:math.hypot(s['mpos'][0]-s['ppos'][0],s['mpos'][2]-s['ppos'][2])
    return (d(pts[0])-d(pts[-1]))/((pts[-1]['ticks']-pts[0]['ticks'])/20)

def player_speed(history,ticks=8):
    """The player's horizontal speed in blocks per second over the last `ticks` game ticks."""
    import math
    pts=[s for s in history if len(s['ppos'])==3]
    if len(pts)<2:return 0.0
    a=next((s for s in pts if pts[-1]['ticks']-s['ticks']<=ticks),pts[0]);b=pts[-1]
    if b['ticks']==a['ticks']:return 0.0
    return math.hypot(b['ppos'][0]-a['ppos'][0],b['ppos'][2]-a['ppos'][2])/((b['ticks']-a['ticks'])/20)

MAX_HP={'zombie':20,'husk':20,'skeleton':20,'stray':20,'spider':16,'cave_spider':12,'creeper':20,'witch':26,'pillager':24,'vindicator':24}

def base_view(s,g,body,hits,mem,history):
    now=time.monotonic();ev=damage_events(hits)
    recent=lambda kind,sec:[e for e in ev if e[1]==kind and now-e[0]<=sec]
    last=lambda kind:next((now-e[0] for e in reversed(ev) if e[1]==kind),None)
    return dict(mob=s['mob'],t=s['ticks']/20,left=90-s['ticks']/20,php=s['php'],mhp=s['mhp'],mhp_max=MAX_HP[s['mob']],
                hdist=g['hdist'],reach=g['reach'],dy=g['dy'],yaw_err=g['yaw_err'],pitch_err=g['pitch_err'],cool=body.cooldown(),
                closing=closing_speed(history,s['mob']),hits_dealt_3s=len(recent('dealt',3)),hits_taken_3s=len(recent('taken',3)),
                since_dealt=last('dealt'),since_taken=last('taken'),arrows=s['arrows'],on_ground=s['pground'],
                mob_hurt=s['mhurt']>0,last=mem['last'])
