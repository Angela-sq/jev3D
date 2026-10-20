#!/usr/bin/env python3
"""Evaluator collector: preserves every attempt and builds the results CSV."""
import csv,json,subprocess,sys,statistics
from config import OUT,VM,guest_trial_dir
FIELDS=['trial_id','rerun_of','amends','scored','mob','site','repeat','model','reasoning_effort','agent_task','outcome','game_seconds','wall_seconds','kills','health_remaining','damage_taken_stat','damage_dealt_stat','escaped','intruders','actions','observations','observation_to_action_median_ms','observation_to_action_max_ms','transport_median_ms','agent_wall_seconds','tool_calls','violations','models_reported','cli_version','video','events','action_log','transcript','technical_reason','actor_note']
def sync(n):
    remote=guest_trial_dir(n)
    if subprocess.run(['limactl','shell',VM,'test','-f',remote+'/complete']).returncode:raise RuntimeError('Trial evidence not finalized')
    local=OUT/'trials'/f'trial-{n:03d}';local.mkdir(parents=True,exist_ok=True)
    tar=subprocess.Popen(['limactl','shell',VM,'tar','-C',remote,'-cf','-','.'],stdout=subprocess.PIPE)
    subprocess.run(['tar','-C',str(local),'-xf','-'],stdin=tar.stdout,check=True)
    if tar.wait():raise RuntimeError('tar from guest failed')
def load(path,default):
    return json.loads(path.read_text()) if path.exists() else default
def jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
def rebuild():
    S=json.loads((OUT/'schedule.json').read_text())
    rows=[]
    for t in S['calibration']+S['trials']+S['reruns']+S['amendments']:
        d=OUT/'trials'/f"trial-{t['trial_id']:03d}"
        if not d.exists():continue
        result=load(d/'result.json',{'outcome':'pending'});meta=load(d/'actor.json',{})
        events=jsonl(d/'actions.jsonl');transport=jsonl(d/'transport.jsonl')
        last=None;delays=[]
        for event in events:
            if event['kind']=='observation':last=event['capture_end_ns']
            elif event['kind']=='action' and last:delays.append((event['start_ns']-last)/1e6)
        if result.get('outcome')=='death':result['health_remaining']=0
        start=result.get('start_observed_wall_ns');end=result.get('end_observed_wall_ns')
        row={k:t.get(k,'') for k in FIELDS}
        row.update({k:result[k] for k in ['outcome','game_seconds','kills','health_remaining','damage_taken_stat','damage_dealt_stat','escaped','intruders'] if k in result})
        row.update(agent_task=meta.get('task',''),actor_note=meta.get('note',''),tool_calls=meta.get('tool_calls',''),violations=len(meta.get('violations',[])),
                   models_reported=' '.join(meta.get('models_reported',[])),cli_version=meta.get('cli_version',''),
                   agent_wall_seconds=round((meta['agent_end_ns']-meta['agent_start_ns'])/1e9,3) if meta.get('agent_end_ns') else '',
                   wall_seconds=round((end-start)/1e9,3) if start and end else '',
                   actions=sum(e['kind']=='action' for e in events),observations=sum(e['kind']=='observation' for e in events),
                   observation_to_action_median_ms=round(statistics.median(delays),2) if delays else '',
                   observation_to_action_max_ms=round(max(delays),2) if delays else '',
                   transport_median_ms=round(statistics.median([(e['response_ns']-e['request_ns'])/1e6 for e in transport]),2) if transport else '',
                   technical_reason=result.get('reason',''))
        for col,file in [('video','video.mp4'),('events','events.log'),('action_log','actions.jsonl'),('transcript','transcript.jsonl')]:
            row[col]=str((d/file).relative_to(OUT)) if (d/file).exists() else ''
        rows.append(row)
    with (OUT/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    return rows
if __name__=='__main__':
    if len(sys.argv)>1:sync(int(sys.argv[1]))
    rows=rebuild();print(json.dumps({'attempts':len(rows),'completed':sum(r['outcome']!='pending' for r in rows)}))
