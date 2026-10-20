#!/usr/bin/env python3
"""Trial transport/evaluator. Scored actor may call begin, act and observe only."""
import os,sys,json,time,subprocess,signal,hashlib,fcntl
from pathlib import Path
from core import validate_action,parse_end,KEYS
os.environ['DISPLAY']=':99'
ROOT=Path.home()/'minecraft-lab/benchmark';ROOT.mkdir(exist_ok=True)
GAME=Path.home()/'.local/share/PrismLauncher/instances/26.3/minecraft'
LOG=GAME/'logs/latest.log'
def run(*cmd):return subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def append(path,event):
    with path.open('a') as f:f.write(json.dumps(event)+'\n')
def release():
    run('xdotool','keyup',*sorted(KEYS))
    for b in [1,3]:run('xdotool','mouseup',str(b))
def command(s):run('python3',str(Path.home()/'minecraft-lab/command.py'),s)
def capture(d):
    n=len(list(d.glob('obs-*.png')));p=d/f'obs-{n:04d}.png';start=time.time_ns()
    run('scrot','--overwrite','-a','212,120,854,480',str(p))
    event={'kind':'observation','capture_start_ns':start,'capture_end_ns':time.time_ns(),'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    append(d/'actions.jsonl',event)
    return {'image':str(p),'ended':(d/'result.json').exists()}
def supervise(n,offset):
    d=ROOT/f'trial-{n:03d}'
    with (d/'video.log').open('w') as vlog:
        video=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','15','-video_size','854x480','-i',':99.0+212,120','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(d/'video.mp4')],stdout=vlog,stderr=vlog)
        (d/'ready').write_text('ready')
        deadline=time.monotonic()+125;result=None;lines=[];began=None
        with LOG.open() as log:
            log.seek(offset)
            while time.monotonic()<deadline:
                line=log.readline()
                if not line:time.sleep(.05);continue
                if '[CHAT] PVE_' in line:
                    lines.append(line)
                    if f'[CHAT] PVE_START|{n}' in line:began=time.time_ns()
                    result=parse_end(line,n)
                    if result:break
        if result is None:
            result={'trial_id':n,'outcome':'technical','reason':'no terminal event within 125 wall seconds'}
            with (ROOT/'input.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);release();command('function pve:end/technical')
        result['start_observed_wall_ns']=began;result['end_observed_wall_ns']=time.time_ns()
        (d/'events.log').write_text(''.join(lines))
        (d/'result.json').write_text(json.dumps(result,indent=2))
        time.sleep(.4)
        run('scrot','--overwrite','-a','212,120,854,480',str(d/'terminal.png'))
        video.send_signal(signal.SIGINT)
        try:video.wait(timeout=10)
        except subprocess.TimeoutExpired:video.kill();video.wait()
        (d/'complete').write_text('complete')
def main():
    op=sys.argv[1]
    if op=='supervise':supervise(int(sys.argv[2]),int(sys.argv[3]));return
    if op=='begin':
        n=int(sys.argv[2]);assert 1<=n<=39
        d=ROOT/f'trial-{n:03d}'
        if d.exists():raise RuntimeError('Trial already attempted; refusing overwrite')
        d.mkdir();(ROOT/'current').write_text(str(n));offset=LOG.stat().st_size
        subprocess.Popen([sys.executable,__file__,'supervise',str(n),str(offset)],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=(d/'supervisor.log').open('w'))
        for _ in range(100):
            if (d/'ready').exists():break
            time.sleep(.05)
        else:raise RuntimeError('Recorder not ready')
        with (ROOT/'input.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);release();run('xdotool','key','1');command(f'function pve:trial/{n}')
        time.sleep(.3);print(json.dumps(capture(d)));return
    n=int((ROOT/'current').read_text());d=ROOT/f'trial-{n:03d}'
    if op=='observe':print(json.dumps(capture(d)));return
    if op!='act':raise ValueError('Unknown operation')
    a=validate_action(json.loads(sys.argv[2]))
    if (d/'result.json').exists():print(json.dumps(capture(d)));return
    event={'kind':'action','action':a,'start_ns':time.time_ns()}
    with (ROOT/'input.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            if a['dx'] or a['dy']:run('xdotool','mousemove_relative','--',str(a['dx']),str(a['dy']))
            if a['keys']:run('xdotool','keydown',*a['keys'])
            for b in a['buttons']:run('xdotool','mousedown',str(b))
            time.sleep(a['ms']/1000)
        except BaseException as e:event['error']=type(e).__name__;raise
        finally:release();event['end_ns']=time.time_ns();append(d/'actions.jsonl',event)
    time.sleep(.05);print(json.dumps(capture(d)))
if __name__=='__main__':main()
