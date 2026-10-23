#!/usr/bin/env python3
"""Evaluator collector: preserves every attempt and builds the requested CSV."""
import csv,json,subprocess,sys,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'experiments/minecraft-pve-2026-10-22-v3'
S=json.loads((ROOT/'schedule.json').read_text())
FIELDS=['trial_id','scored','site','encounter','repeat','model','reasoning_effort','agent_task','outcome','game_seconds','wall_seconds','kills','health_remaining','damage_taken_stat','damage_dealt_stat','actions','observations','observation_to_action_median_ms','observation_to_action_max_ms','transport_median_ms','video','events','action_log','technical_reason','actor_note','controller_version','known_control_issue']
def sync(n):
    remote=f'/home/sathvikr.guest/minecraft-lab/benchmark-v3-oct22/trial-{n:03d}'
    check=subprocess.run(['limactl','shell','minecraft-lab','test','-f',remote+'/complete'])
    if check.returncode:raise RuntimeError('Trial evidence not finalized')
    (ROOT/'trials').mkdir(exist_ok=True)
    subprocess.run(['limactl','copy','-r','minecraft-lab:'+remote,str(ROOT/'trials'/f'trial-{n:03d}')],check=True)
def rebuild():
    rows=[]
    for t in S['trials']:
        d=ROOT/'trials'/f"trial-{t['trial_id']:03d}"
        if not d.exists():continue
        result=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else {'outcome':'pending'}
        events=[json.loads(s) for s in (d/'actions.jsonl').read_text().splitlines()] if (d/'actions.jsonl').exists() else []
        transport=[json.loads(s) for s in (d/'transport.jsonl').read_text().splitlines()] if (d/'transport.jsonl').exists() else []
        meta=json.loads((d/'actor.json').read_text()) if (d/'actor.json').exists() else {}
        last=None;delays=[]
        for event in events:
            if event['kind']=='observation':last=event['capture_end_ns']
            elif event['kind']=='action' and last:delays.append((event['start_ns']-last)/1e6)
        if result.get('outcome')=='death': result['health_remaining']=0
        start=result.get('start_observed_wall_ns');end=result.get('end_observed_wall_ns')
        row={k:t.get(k,'') for k in FIELDS};row.update({k:result[k] for k in ['outcome','game_seconds','kills','health_remaining','damage_taken_stat','damage_dealt_stat'] if k in result})
        row.update(agent_task=meta.get('task',''),actor_note=meta.get('note',''),wall_seconds=round((end-start)/1e9,3) if start and end else '',actions=sum(e['kind']=='action' for e in events),observations=sum(e['kind']=='observation' for e in events),observation_to_action_median_ms=round(statistics.median(delays),2) if delays else '',observation_to_action_max_ms=round(max(delays),2) if delays else '',transport_median_ms=round(statistics.median([(e['response_ns']-e['request_ns'])/1e6 for e in transport]),2) if transport else '',technical_reason=result.get('reason',''))
        for col,file in [('video','video.mp4'),('events','events.log'),('action_log','actions.jsonl')]:row[col]=str((d/file).relative_to(ROOT)) if (d/file).exists() else ''
        row.update(controller_version='v3-persistent-controls',known_control_issue='')
        rows.append(row)
    with (ROOT/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    print(json.dumps({'attempts':len(rows),'completed':sum(r['outcome']!='pending' for r in rows),'scored_completed':sum(r['scored'] and r['outcome']!='pending' for r in rows)}))
if __name__=='__main__':
    if len(sys.argv)>1:sync(int(sys.argv[1]))
    rebuild()
