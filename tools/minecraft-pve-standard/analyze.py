#!/usr/bin/env python3
"""Audit recorded evidence and summarize the standard PvE benchmark; never controls play."""
import csv,hashlib,json,math,statistics,subprocess
from collections import Counter
from pathlib import Path
from config import OUT,REPO,VM,guest_trial_dir
from core import parse_end,MOBS
VALID=('win','death','timeout','target_lost')

def wilson(wins,n):
    if not n:return None
    z=1.959963984540054;p=wins/n;den=1+z*z/n
    middle=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [0 if wins==0 else max(0,middle-half),1 if wins==n else min(1,middle+half)]

def med(xs):
    xs=[float(x) for x in xs if x not in ('',None)]
    return statistics.median(xs) if xs else None

def summarize(rows):
    outcomes=Counter(r['outcome'] for r in rows)
    valid=[r for r in rows if r['outcome'] in VALID]
    return dict(attempts=len(rows),outcomes=dict(outcomes),valid_trials=len(valid),
                win_rate=outcomes['win']/len(valid) if valid else None,wilson_95=wilson(outcomes['win'],len(valid)),
                median_game_seconds=med(r['game_seconds'] for r in valid),
                median_damage_dealt_stat=med(r['damage_dealt_stat'] for r in valid),
                trials_with_damage_dealt=sum(int(r['damage_dealt_stat'] or 0)>0 for r in valid))

def effective(rows,schedule):
    """One row per scheduled condition: the rerun replaces a technical original."""
    by={int(r['trial_id']):r for r in rows}
    out=[]
    for t in schedule['trials']:
        n=t['trial_id'];r=by.get(n)
        if 200+n in by:n+=200;r=by[n]   # amendment 1 replaces the daylight spider trial
        if r and r['outcome']=='technical' and 100+n in by:r=by[100+n]
        if r and r['outcome']!='pending':out.append(r)
    return out

def audit_trial(row,errors,checks):
    n=int(row['trial_id']);d=OUT/'trials'/f'trial-{n:03d}'
    meta=json.loads((d/'actor.json').read_text()) if (d/'actor.json').exists() else {}
    if meta.get('violations'):errors.append(f'{n}: {len(meta["violations"])} tool-use violations')
    if meta.get('models_reported') not in (['claude-fable-5-1'],None):errors.append(f'{n}: models reported {meta.get("models_reported")}')
    for k in ('mcp_servers','skills'):
        if meta.get(k):errors.append(f'{n}: actor loaded {k}')
    if any(p.get('path')!='builtin' for p in meta.get('plugins',[])):errors.append(f'{n}: actor loaded a non-builtin plugin')
    if meta.get('tools_loaded') and sorted(meta['tools_loaded'])!=['Bash','Read']:errors.append(f'{n}: actor tools {meta["tools_loaded"]}')
    if row['outcome']=='technical':return []
    for f in ['result.json','events.log','actions.jsonl','transport.jsonl','video.mp4','terminal.png','complete','actor.json','transcript.jsonl']:
        if not (d/f).is_file():errors.append(f'{n}: missing {f}')
    ends=[e for e in (parse_end(l,n) for l in (d/'events.log').read_text().splitlines()) if e] if (d/'events.log').exists() else []
    if len(ends)!=1:errors.append(f'{n}: expected exactly one terminal event')
    else:
        for k in ['outcome','kills','damage_taken_stat','damage_dealt_stat','escaped','intruders']:
            if str(ends[0][k])!=row[k]:errors.append(f'{n}: {k} mismatch')
        for k in ['health_remaining','game_seconds']:
            if float(ends[0][k])!=float(row[k]):errors.append(f'{n}: {k} mismatch')
    actions=[json.loads(s) for s in (d/'actions.jsonl').read_text().splitlines()] if (d/'actions.jsonl').exists() else []
    inits=[e for e in actions if e['kind']=='input_initialization'];obs=[e for e in actions if e['kind']=='observation']
    if len(inits)!=1 or not obs or inits[0]['time_ns']>=obs[0]['capture_start_ns']:errors.append(f'{n}: input initialization missing or late')
    raw=json.loads((d/'result.json').read_text());begin=raw.get('start_observed_wall_ns');end=raw.get('end_observed_wall_ns')
    fraction=None
    if begin and end and end>begin:
        fraction=sum(max(0,min(e['end_ns'],end)-max(e['start_ns'],begin)) for e in actions if e['kind']=='action')/(end-begin)
    last=None;delays=[]
    for e in actions:
        if e['kind']=='observation':
            p=d/Path(e['path']).name
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:errors.append(f'{n}: observation hash mismatch {p.name}')
            last=e['capture_end_ns']
        elif e['kind']=='action':
            if last:delays.append((e['start_ns']-last)/1e6)
            if 'error' in e:errors.append(f'{n}: input error {e["error"]}')
    probe=subprocess.run(['limactl','shell',VM,'ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames:format=duration','-of','json',guest_trial_dir(n)+'/video.mp4'],capture_output=True,text=True)
    if probe.returncode:errors.append(f'{n}: video cannot be decoded')
    else:
        info=json.loads(probe.stdout);stream=info['streams'][0];seconds=float(info['format']['duration'])
        if (stream['width'],stream['height'])!=(854,480):errors.append(f'{n}: wrong video dimensions')
        if row['wall_seconds'] and seconds<float(row['wall_seconds']):errors.append(f'{n}: video shorter than active battle')
        checks.append(dict(trial_id=n,video_seconds=seconds,frames=int(stream.get('nb_frames',0)),screenshots=len(obs),action_fraction=fraction))
    return delays

def main():
    rows=list(csv.DictReader((OUT/'results.csv').open()))
    schedule=json.loads((OUT/'schedule.json').read_text())
    errors=[];checks=[];delays=[]
    for r in rows:
        if r['outcome']=='pending':continue
        trial_delays=audit_trial(r,errors,checks)
        if r['scored']=='True':delays+=trial_delays
    frozen=OUT/'frozen-sha256.json'
    if frozen.exists():
        for p,digest in json.loads(frozen.read_text()).items():
            if hashlib.sha256((REPO/p).read_bytes()).hexdigest()!=digest:errors.append(f'Frozen file changed: {p}')
    else:errors.append('frozen-sha256.json missing')
    scored=effective(rows,schedule)
    fractions=[c['action_fraction'] for c in checks if c['action_fraction'] is not None]
    output=dict(expected_scored=len(schedule['trials']),completed_scored=len(scored),overall=summarize(scored),
                by_mob={m:summarize([r for r in scored if r['mob']==m]) for m in MOBS},
                by_site={s['site']:summarize([r for r in scored if r['site']==s['site']]) for s in schedule['sites']},
                calibration=summarize([r for r in rows if r['scored']=='False']),
                technical_reruns=[int(r['trial_id']) for r in rows if r['rerun_of']],
                superseded_by_amendment=[int(r['amends']) for r in rows if r['amends'] and not r['rerun_of']],
                observation_to_action_median_ms=statistics.median(delays) if delays else None,
                observation_to_action_max_ms=max(delays) if delays else None,
                median_action_execution_fraction_wall=statistics.median(fractions) if fractions else None,
                escaped_trials=[int(r['trial_id']) for r in scored if r['escaped'] not in ('','0')],
                intruder_trials=[int(r['trial_id']) for r in scored if r['intruders'] not in ('','0')],
                audit_errors=errors,evidence_checks=checks,
                missing_trial_ids=[t['trial_id'] for t in schedule['trials'] if not any(int(r['trial_id'])%100==t['trial_id'] for r in scored)],
                limitations=['Fixed scenarios at three sites; repeated layouts are not independent terrain samples.',
                             'Five trials per mob: per-mob intervals are wide.',
                             'Latency includes model reasoning, orchestration, screenshot transport and tool execution.',
                             'Inputs release after at most one second; shield and movement are not held while thinking.',
                             'No human, scripted, no-action or unlimited-time comparison included.',
                             'Software-rendered VM; not pooled with the Astra cohorts.'])
    (OUT/'summary.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['completed_scored','overall','audit_errors','missing_trial_ids']},indent=2))

if __name__=='__main__':main()
