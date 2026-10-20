#!/usr/bin/env python3
"""Guest-only post-run input diagnostic. NEVER execute during scored trials.

No fighting or agent decisions: known camera deltas with F3 visible to verify
the input mapping. Output is explicitly outside the scored dataset.
"""
import json
import os
import subprocess
import time
from pathlib import Path

os.environ['DISPLAY']=':99'
home=Path.home()
out=home/'minecraft-lab/camera-diagnostic'

def run(*args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)

def command(s):
    run('python3',str(home/'minecraft-lab/command.py'),s)

def main():
    # Prevent accidentally running alongside any unfinished guest trial.
    root=home/'minecraft-lab/benchmark'
    for trial in root.glob('trial-*'):
        if not (trial/'complete').exists():
            raise RuntimeError('Unfinished trial: '+str(trial))
    if not (root/'trial-039/complete').exists():
        raise RuntimeError('The declared scored run is not complete')
    out.mkdir(exist_ok=False)
    run('xdotool','keyup','w','a','s','d','space','Shift_L','Control_L')
    run('xdotool','mouseup','1');run('xdotool','mouseup','3')
    command('gamemode creative @a')
    command('kill @e[tag=pve_enemy]')
    command('worldborder center 240.5 -240.5')
    command('execute positioned 240.5 100 -240.5 positioned over motion_blocking_no_leaves run tp @a ~ ~1 ~ 0 0')
    command('title @a clear')
    run('xdotool','key','F3')
    steps=[('initial',0,0),('right_100',100,0),('right_100_again',100,0),('left_100',-100,0),('down_100',0,100),('up_100',0,-100)]
    journal=[]
    for name,dx,dy in steps:
        start=time.time_ns()
        if dx or dy:run('xdotool','mousemove_relative','--',str(dx),str(dy))
        time.sleep(.5)
        run('scrot','--overwrite','-a','212,120,854,480',str(out/(name+'.png')))
        journal.append(dict(name=name,dx=dx,dy=dy,start_ns=start,capture_done_ns=time.time_ns()))
    run('xdotool','key','F3')
    (out/'steps.json').write_text(json.dumps(journal,indent=2)+'\n')

if __name__=='__main__':main()
