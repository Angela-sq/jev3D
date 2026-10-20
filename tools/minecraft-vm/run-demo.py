#!/usr/bin/env python3
from pathlib import Path
import json,os
root=Path.home()/'minecraft-lab/demo'
os.environ.update(DISPLAY=':99',LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='6')
os.chdir(root)
cmd=json.loads((root/'demo-command.json').read_text())
assert '--demo' in cmd, 'This runner is exclusively for built-in demo mode'
os.execv(cmd[0],cmd)
