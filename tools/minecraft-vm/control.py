#!/usr/bin/env python3
"""Pixel-only guest controller. All input belongs to DISPLAY=:99, never the host."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

os.environ['DISPLAY'] = ':99'
ROOT = Path.home() / 'minecraft-lab'

def bounded(value, lo, hi):
    number = int(value)
    if not lo <= number <= hi:
        raise argparse.ArgumentTypeError(f'must be between {lo} and {hi}')
    return number

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest='action', required=True)
    s.add_parser('status')
    c = s.add_parser('capture'); c.add_argument('path')
    k = s.add_parser('key'); k.add_argument('key', choices=['w','a','s','d','space','Escape','e','1','2','3','Shift_L','Control_L','Return','Tab','F3','F2','F11']); k.add_argument('ms', type=lambda x:bounded(x,0,1000))
    m = s.add_parser('look'); m.add_argument('dx',type=lambda x:bounded(x,-300,300)); m.add_argument('dy',type=lambda x:bounded(x,-300,300))
    c = s.add_parser('click'); c.add_argument('button',type=int,choices=[1,3]); c.add_argument('ms',type=lambda x:bounded(x,0,1000),default=50,nargs='?')
    c = s.add_parser('point'); c.add_argument('x',type=lambda x:bounded(x,0,1279)); c.add_argument('y',type=lambda x:bounded(x,0,719))
    s.add_parser('release')
    return p

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def main():
    args = parser().parse_args()
    ROOT.mkdir(exist_ok=True)
    result = {'action':vars(args),'started_ns':time.monotonic_ns(),'utc_epoch':time.time()}
    if args.action == 'status':
        result['windows'] = run('wmctrl','-l') if subprocess.call(['which','wmctrl'],stdout=subprocess.DEVNULL) == 0 else run('xdotool','search','--onlyvisible','--name','.*')
    elif args.action == 'capture':
        path = Path(args.path).expanduser().resolve()
        path.parent.mkdir(parents=True,exist_ok=True)
        run('scrot','--overwrite',str(path))
        result['path'] = str(path)
    elif args.action == 'key':
        try:
            run('xdotool','keydown',args.key)
            time.sleep(args.ms/1000)
        finally:
            run('xdotool','keyup',args.key)
    elif args.action == 'look':
        run('xdotool','mousemove_relative','--',str(args.dx),str(args.dy))
    elif args.action == 'point':
        run('xdotool','mousemove',str(args.x),str(args.y))
    elif args.action == 'click':
        try:
            run('xdotool','mousedown',str(args.button))
            time.sleep(args.ms/1000)
        finally:
            run('xdotool','mouseup',str(args.button))
    elif args.action == 'release':
        run('xdotool','keyup','w','a','s','d','space','Shift_L','Control_L')
        for button in ('1','3'): run('xdotool','mouseup',button)
    result['finished_ns'] = time.monotonic_ns()
    with (ROOT/'control.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
    print(json.dumps(result))

if __name__ == '__main__': main()
