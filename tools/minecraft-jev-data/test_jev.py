"""Checks that need no VM or Jev calls: python3 -m pytest test_jev.py"""
import json,sys,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import validate_action

def player():
    # jev_player imports guest_trial (guest-only paths); stub it and the key file.
    sys.modules['guest_trial']=types.SimpleNamespace(ROOT=Path('.'),LOG=Path('.'))
    import importlib,unittest.mock as m
    with m.patch.object(Path,'read_text',lambda self,*a,**k:'test-key'):
        return importlib.import_module('jev_player')

def test_every_action_is_a_legal_input():
    for name,(rule,prims) in player().ACTIONS.items():
        assert rule and prims
        for a in prims:validate_action(a)

def test_hit_line_parses():
    m=player().HIT.search('[01:02:03] [Render thread/INFO]: [System] [CHAT] PVE_HIT|401|57|1650|38|35')
    assert m and list(map(int,m.groups()))==[401,57,1650,38,35]

def test_schedule_copies_standard_setups():
    out=Path(__file__).resolve().parents[2]/'experiments/minecraft-jev-data-2026-10-23'
    s=json.loads((out/'schedule.json').read_text())
    assert len(s['pilot'])==5 and len(s['batch'])==50
    for t in s['pilot']+s['batch']:
        f=(out/f"datapack/data/jevdata/function/trial/{t['trial_id']}.mcfunction").read_text()
        assert f'scoreboard players set #id pve {t["trial_id"]}\n' in f and f'summon {t["mob"]} ' in f
