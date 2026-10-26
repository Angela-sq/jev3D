"""v7: after v6 on the dev fights (9/10). What v6 lost and what changed:
  - creeper: it came within 2.9 blocks, a poke missed, the fuse lit; the player backed off at ~2 blocks/s because
    `poke` stepped back in between, and it exploded. A swelling creeper stands still, and the fuse runs back down once
    you are 7+ blocks away, so walking straight back (4.3 blocks/s) from 3 to 7 blocks takes ~1 s of the 1.5 s. Now
    a fuse reflex in the body tracks the swell (up within 7 blocks once lit, down beyond) and backs off without stopping
    until it has run down; then poking resumes."""
from harness.v6 import INTERVAL,QUESTION,TACTICS,MOVES,view,options,describe,adjust as v6_adjust
import time

def adjust(tac,s,g,body):
    tac=v6_adjust(tac,s,g,body)
    if s['mob']!='creeper':return tac
    now=time.monotonic();dt=min(.2,now-getattr(body,'fuse_t',now));body.fuse_t=now
    swell=getattr(body,'swell',0.0)
    if swell>0 or g['dist3']<3.0:swell=max(0.0,swell+(dt if g['dist3']<7 else -dt)) if swell>0 else dt
    body.swell=swell
    if swell>0:tac.update(keys=['s'],sprint=False,jump=False,shield=False)
    return tac
