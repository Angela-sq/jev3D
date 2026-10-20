#!/usr/bin/env python3
"""Evaluator-only in-game command entry. Never permitted to the scored actor."""
import os,sys,subprocess,time
os.environ['DISPLAY']=':99'
command=sys.argv[1]
assert '\n' not in command and len(command)<2000
subprocess.run(['xdotool','key','slash'],check=True)
time.sleep(.15)
subprocess.run(['xdotool','type','--clearmodifiers','--delay','1',command.lstrip('/')],check=True)
subprocess.run(['xdotool','key','Return'],check=True)
time.sleep(.2)
