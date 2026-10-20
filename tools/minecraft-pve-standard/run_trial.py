#!/usr/bin/env python3
"""Run one trial with a fresh, isolated Fable actor; never chooses actions itself.

Exit codes: 0 trial recorded, 3 infrastructure problem that must stop the run.
"""
import json,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from config import OUT,TOOLS,VM,MODEL,EFFORT,guest_trial_dir
import collect
ACTOR=TOOLS/'actor.py'
AGENT_TIMEOUT_S=240
RATE_LIMIT_RE=re.compile(r'rate.?limit|usage limit|limit reached|\b429\b|overloaded|too many requests',re.I)
AUTH_RE=re.compile(r'\bauth|/login|log ?in|api key|unauthori[sz]ed|\b401\b',re.I)

def condition(n):
    s=json.loads((OUT/'schedule.json').read_text())
    return next(t for t in s['trials']+s['reruns']+s['amendments']+s['calibration'] if t['trial_id']==n)

def guest(*cmd):
    return subprocess.run(['limactl','shell',VM,*cmd],capture_output=True,text=True)

def args(n,mcp):
    obs=f"//{str(OUT/'trials'/f'trial-{n:03d}').lstrip('/')}/obs-*.png"
    return [shutil.which('claude') or 'claude','-p','--model',MODEL,'--effort',EFFORT,
            '--output-format','stream-json','--verbose',
            '--tools','Bash,Read','--allowedTools',f'Bash(python3 {ACTOR}:*)',f'Read({obs})',
            '--strict-mcp-config','--mcp-config',str(mcp),'--setting-sources','','--disable-slash-commands']

def audit(events,n):
    """Every tool call must be actor.py begin/act/observe for this trial, or Read of its screenshot."""
    violations=[];calls=0
    obs_dir=str(OUT/'trials'/f'trial-{n:03d}')+'/'
    begin=re.compile(rf"^python3 {re.escape(str(ACTOR))} (begin {n}|act '[^']*'|observe)$")
    for e in events:
        if e.get('type')!='assistant':continue
        for c in e['message'].get('content',[]):
            if c.get('type')!='tool_use':continue
            calls+=1;inp=c.get('input',{})
            if c['name']=='Bash' and begin.match(inp.get('command','').strip()):continue
            if c['name']=='Read' and inp.get('file_path','').startswith(obs_dir) and re.search(r'/obs-\d{4}\.png$',inp['file_path']):continue
            violations.append({'tool':c['name'],'input':inp})
    return calls,violations

def main():
    n=int(sys.argv[1]);t=condition(n)
    d=OUT/'trials'/f'trial-{n:03d}'
    if d.exists():sys.exit(f'trial {n} already attempted; refusing overwrite')
    prompt=(OUT/'ACTOR_PROMPT.md').read_text().replace('{ACTOR}',str(ACTOR)).replace('{TRIAL_ID}',str(n))
    cwd=Path(tempfile.mkdtemp(prefix='pve-actor-'))
    mcp=Path(tempfile.mkdtemp(prefix='pve-mcp-'))/'empty-mcp.json';mcp.write_text('{"mcpServers":{}}')
    env=dict(os.environ,CLAUDE_CODE_DISABLE_AUTO_MEMORY='1');env.pop('ANTHROPIC_API_KEY',None)
    start=time.time_ns()
    p=subprocess.Popen(args(n,mcp),cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:out,err=p.communicate(prompt,timeout=AGENT_TIMEOUT_S);killed=False
    except subprocess.TimeoutExpired:p.kill();out,err=p.communicate();killed=True
    end=time.time_ns()
    d.mkdir(parents=True,exist_ok=True)
    (d/'transcript.jsonl').write_text(out);(d/'agent-stderr.log').write_text(err)
    events=[]
    for line in out.splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    init=next((e for e in events if e.get('type')=='system' and e.get('subtype')=='init'),{})
    result=next((e for e in reversed(events) if e.get('type')=='result'),{})
    models=sorted((result.get('modelUsage') or {}).keys())
    calls,violations=audit(events,n)
    began=bool(guest('test','-d',guest_trial_dir(n)).returncode==0)
    if began:
        for _ in range(300):
            if guest('test','-f',guest_trial_dir(n)+'/complete').returncode==0:break
            time.sleep(.5)
    meta={'task':result.get('session_id') or init.get('session_id',''),'note':result.get('result',''),
          'model_requested':MODEL,'reasoning_effort':EFFORT,'models_reported':models,
          'cli_version':init.get('claude_code_version',''),'tools_loaded':init.get('tools',[]),
          'mcp_servers':init.get('mcp_servers',[]),'slash_commands':init.get('slash_commands',[]),
          'skills':init.get('skills',[]),'plugins':init.get('plugins',[]),
          'agent_start_ns':start,'agent_end_ns':end,'agent_killed_at_timeout':killed,
          'tool_calls':calls,'violations':violations,'num_turns':result.get('num_turns'),
          'image_delivery':'Read tool on 854x480 PNG','condition':t}
    (d/'actor.json').write_text(json.dumps(meta,indent=2)+'\n')
    if began:collect.sync(n)
    else:(d/'result.json').write_text(json.dumps({'trial_id':n,'outcome':'technical','reason':'actor never began the trial'},indent=2))
    collect.rebuild()
    blob=f"{result.get('result','')} {err[-2000:]}"
    stop=None
    if result.get('is_error') or not result:
        stop='rate_limit' if RATE_LIMIT_RE.search(blob) else 'auth' if AUTH_RE.search(blob) else None
    if models and models!=[MODEL]:stop='model_identity'
    print(json.dumps({'trial':n,'outcome':json.loads((d/'result.json').read_text())['outcome'],'tool_calls':calls,'violations':len(violations),'stop':stop}))
    if stop:sys.exit(3)

if __name__=='__main__':main()
