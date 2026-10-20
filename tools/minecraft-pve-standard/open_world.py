#!/usr/bin/env python3
"""Evaluator setup: start Minecraft 26.3 in the VM and open the benchmark world (menu clicks only)."""
import subprocess,time
from config import VM
LOG='.local/share/PrismLauncher/instances/26.3/minecraft/logs/latest.log'
def sh(cmd,check=True):return subprocess.run(['limactl','shell',VM,'bash','-c',cmd],capture_output=True,text=True,check=check).stdout
def click(x,y):
    sh(f'DISPLAY=:99 xdotool mousemove {x} {y} mousedown 1 sleep 0.05 mouseup 1')
def wait_for(pattern,seconds):
    for _ in range(seconds):
        if sh(f'grep -acF {pattern!r} ~/{LOG} || true').strip() not in ('','0'):return True
        time.sleep(1)
    raise SystemExit(f'timed out waiting for {pattern!r}')
def main():
    sh('pkill -f "[j]ava.*minecraft" || true; sleep 3; systemctl --user start minecraft-launcher; sleep 3')
    sh('nohup ~/.local/bin/minecraft-launcher --launch 26.3 >/dev/null 2>&1 &')
    time.sleep(5);wait_for('Created: 512x512x0 minecraft:textures/atlas/chest.png-atlas',240)
    time.sleep(5)
    sh('DISPLAY=:99 wmctrl -c "Console window" || true; sleep 1; DISPLAY=:99 wmctrl -a "Minecraft 26.3"')
    click(638,355);time.sleep(2)   # Singleplayer
    click(600,255);time.sleep(.5)  # the only world
    click(480,515)                 # Play Selected World
    wait_for('PVE evaluator loaded',180);time.sleep(5)
    print('world open')
if __name__=='__main__':main()
