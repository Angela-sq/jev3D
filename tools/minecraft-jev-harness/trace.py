#!/usr/bin/env python3
"""Print a fight's decisions in short form, for reading what went wrong: python3 trace.py TRIAL [EVERY]."""
import json,sys
from collections import Counter
from config import OUT
n=int(sys.argv[1]);every=int(sys.argv[2]) if len(sys.argv)>2 else 3
d=OUT/'trials'/f'trial-{n:04d}'
res=json.loads((d/'result.json').read_text())
steps=[json.loads(l) for l in (d/'steps.jsonl').read_text().splitlines() if l.strip()]
print(f"trial {n}: {res['outcome']} at {res.get('game_seconds')} s, dealt {res.get('damage_dealt_stat')}, taken {res.get('damage_taken_stat')}; choices {dict(Counter(s['choice'] for s in steps))}")
for s in steps:
    if s['step']%every and s is not steps[-1]:continue
    v=s['view'];p=s.get('probabilities') or {}
    top=' '.join(f'{k}:{x:.2f}' for k,x in sorted(p.items(),key=lambda kv:-kv[1])[:3])
    print(f"{v['t']:5.1f}s {s['choice']:13s} hd {v['hdist']:5.1f} reach {v['reach']:4.1f} dy {v['dy']:+4.1f} yaw {v['yaw_err']:+5.0f} hp {v['php']:4.1f} mob {v['mhp'] if v['mhp'] is None else round(v['mhp'],1)} close {v['closing']:+4.1f} arrows {v['arrows']} clicks {s['clicks']} | {top}")
