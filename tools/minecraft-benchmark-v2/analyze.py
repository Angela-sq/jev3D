#!/usr/bin/env python3
"""Audit recorded evidence and summarize the fixed PvE pilot; never controls play."""
import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from core import parse_end

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'experiments/minecraft-pve-2026-10-19-v2'

def wilson(wins, n):
    if not n:
        return None
    z = 1.959963984540054
    p = wins / n
    den = 1 + z*z/n
    middle = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [0 if wins==0 else max(0, middle-half), 1 if wins==n else min(1, middle+half)]

def summarize(rows):
    outcomes = Counter(r['outcome'] for r in rows)
    valid = [r for r in rows if r['outcome'] in ('win','death','timeout')]
    return dict(attempts=len(rows), outcomes=dict(outcomes), valid_trials=len(valid),
                win_rate=outcomes['win']/len(valid) if valid else None,
                wilson_95=wilson(outcomes['win'], len(valid)),
                median_game_seconds=statistics.median(float(r['game_seconds']) for r in valid) if valid else None)

def main():
    rows = list(csv.DictReader((OUT/'results.csv').open()))
    scheduled = json.loads((OUT/'schedule.json').read_text())['trials']
    errors=[]; checks=[]; all_delays=[]; durations=[]; active_fractions=[]
    for row in rows:
        n=int(row['trial_id']); d=OUT/'trials'/f'trial-{n:03d}'
        if row['outcome']=='pending':
            continue
        required=['result.json','events.log','actions.jsonl','transport.jsonl','video.mp4','terminal.png','complete','actor.json']
        for f in required:
            if not (d/f).is_file(): errors.append(f'{n}: missing {f}')
        if not (d/'events.log').exists():continue
        events=[parse_end(line,n) for line in (d/'events.log').read_text().splitlines()]
        events=[e for e in events if e]
        if row['outcome']!='technical':
            if len(events)!=1:errors.append(f'{n}: expected exactly one terminal event')
            else:
                event=events[0]
                for k in ['outcome','kills','damage_taken_stat','damage_dealt_stat']:
                    if str(event[k])!=row[k]:errors.append(f'{n}: {k} mismatch')
                for k in ['health_remaining','game_seconds']:
                    if float(event[k])!=float(row[k]):errors.append(f'{n}: {k} mismatch')
        actions=[json.loads(s) for s in (d/'actions.jsonl').read_text().splitlines()]
        initializations=[e for e in actions if e['kind']=='input_initialization']
        observations=[e for e in actions if e['kind']=='observation']
        if len(initializations)!=1 or not observations or initializations[0]['time_ns']>=observations[0]['capture_start_ns']:
            errors.append(f'{n}: input initialization missing or late')
        raw=json.loads((d/'result.json').read_text())
        begin=raw.get('start_observed_wall_ns');end=raw.get('end_observed_wall_ns')
        if row['scored']=='True' and begin and end and end>begin:
            execution_ns=sum(max(0,min(e['end_ns'],end)-max(e['start_ns'],begin))
                             for e in actions if e['kind']=='action')
            active_fractions.append(execution_ns/(end-begin))
        last=None; delays=[]
        for e in actions:
            if e['kind']=='observation':
                p=d/Path(e['path']).name
                if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:
                    errors.append(f'{n}: observation hash mismatch {p.name}')
                last=e['capture_end_ns']
            elif e['kind']=='action':
                if last:delays.append((e['start_ns']-last)/1e6)
                if 'error' in e:errors.append(f'{n}: input error {e["error"]}')
        if row['scored']=='True':all_delays.extend(delays)
        remote=f'/home/sathvikr.guest/minecraft-lab/benchmark-v2/trial-{n:03d}/video.mp4'
        probe=subprocess.run(['limactl','shell','minecraft-lab','ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames:format=duration','-of','json',remote],capture_output=True,text=True)
        if probe.returncode:errors.append(f'{n}: video cannot be decoded')
        else:
            info=json.loads(probe.stdout);stream=info['streams'][0]
            seconds=float(info['format']['duration']);durations.append(seconds)
            if (stream['width'],stream['height'])!=(854,480):errors.append(f'{n}: wrong video dimensions')
            if row['wall_seconds'] and seconds<float(row['wall_seconds']):errors.append(f'{n}: video shorter than active battle')
            if int(stream.get('nb_frames',0))<1:errors.append(f'{n}: video has no frames')
            checks.append(dict(trial_id=n,video_seconds=seconds,frames=int(stream.get('nb_frames',0)),screenshots=sum(e['kind']=='observation' for e in actions)))
        if not row['agent_task']:errors.append(f'{n}: missing actor identity')
    frozen=json.loads((OUT/'frozen-sha256.json').read_text())
    for p,digest in frozen.items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest:errors.append(f'Frozen file changed: {p}')
    scored=[r for r in rows if r['scored']=='True' and r['outcome']!='pending']
    timing_ratios=[float(r['wall_seconds'])/float(r['game_seconds']) for r in scored if r['wall_seconds'] and r['game_seconds'] and float(r['game_seconds'])>0]
    output=dict(expected_scored=36,completed_scored=len(scored),overall=summarize(scored),
                by_encounter={e:summarize([r for r in scored if r['encounter']==e]) for e in ['zombie','two_zombies','skeleton']},
                by_site={s:summarize([r for r in scored if r['site']==s]) for s in ['A','B','C']},
                calibration=summarize([r for r in rows if r['scored']=='False']),
                observation_to_action_median_ms=statistics.median(all_delays) if all_delays else None,
                observation_to_action_max_ms=max(all_delays) if all_delays else None,
                median_action_execution_fraction_wall=statistics.median(active_fractions) if active_fractions else None,
                median_wall_to_game_duration_ratio=statistics.median(timing_ratios) if timing_ratios else None,
                audit_errors=errors,evidence_checks=checks,
                missing_trial_ids=[t['trial_id'] for t in scheduled if str(t['trial_id']) not in {r['trial_id'] for r in rows}],
                limitations=['Fixed scenarios; repeated layouts are not independent terrain samples.',
                             'Latency includes model reasoning, orchestration, screenshot transport and tool execution.',
                             'Inputs release after at most one second; shield and movement are not held while thinking.',
                             'No human, scripted, no-action, Jev, or unlimited-time comparison included.',
                             'Software-rendered VM; model-specific causal claims are not supported.'])
    (OUT/'summary.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['completed_scored','overall','audit_errors','missing_trial_ids']},indent=2))

if __name__=='__main__':main()
