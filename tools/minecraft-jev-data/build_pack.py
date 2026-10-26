#!/usr/bin/env python3
"""Build the jevdata datapack and schedule. Each fight copies a standard PvE setup; only the trial ID changes.
The pack also reports every change in damage dealt or taken (PVE_HIT) so each Jev step gets its result."""
import json,re,shutil
from config import OUT,STANDARD,MODEL
PACK=OUT/'datapack'
SRC=STANDARD/'datapack/data/pve/function/trial'
shutil.rmtree(PACK,ignore_errors=True)
F=PACK/'data/jevdata/function'
def fn(name,lines):
    p=F/(name+'.mcfunction');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(lines)+'\n')
F.mkdir(parents=True)
(PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'Jev data recorder','pack_format':121,'min_format':121,'max_format':121}}))
for tag in ['load','tick']:
    p=PACK/f'data/minecraft/tags/function/{tag}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'values':['jevdata:'+tag]}))
fn('load',['scoreboard objectives add jev dummy','tellraw @a "JEV data pack loaded"'])
fn('tick',['execute if score #phase pve matches 2..3 run function jevdata:hits'])
fn('hits',['scoreboard players operation #dealt jev = @p pve_dealt','scoreboard players operation #taken jev = @p pve_taken',
           'execute unless score #dealt jev = #pdealt jev run function jevdata:emit',
           'execute unless score #taken jev = #ptaken jev run function jevdata:emit'])
fn('emit',['scoreboard players operation #pdealt jev = #dealt jev','scoreboard players operation #ptaken jev = #taken jev',
           'tellraw @a '+json.dumps(['PVE_HIT|',{'score':{'name':'#id','objective':'pve'}},'|',{'score':{'name':'#ticks','objective':'pve'}},'|',{'score':{'name':'#hp','objective':'pve'}},'|',{'score':{'name':'#dealt','objective':'jev'}},'|',{'score':{'name':'#taken','objective':'jev'}}],separators=(',',':'))])
def copy_setup(src,n):
    lines=(SRC/f'{src}.mcfunction').read_text().splitlines()
    out=[f'scoreboard players set #id pve {n}' if re.fullmatch(r'scoreboard players set #id pve -?\d+',l) else l for l in lines]
    assert out.count(f'scoreboard players set #id pve {n}')==1
    return ['scoreboard players set #pdealt jev 0','scoreboard players set #ptaken jev 0',*out]
std=json.loads((STANDARD/'schedule.json').read_text())
def source(t):
    """Standard trial whose setup this fight copies (spiders use their night-time amendment setup)."""
    return 200+t['trial_id'] if t['mob'] in ('spider','cave_spider') else t['trial_id']
# Pilot: 5 zombie fights across the three sites. Batches 1-4: the standard schedule's 50 fights, same order (IDs 500+n ... 800+n).
zombie={t['site']:t for t in std['trials'] if t['mob']=='zombie'}
groups={'pilot':[dict(zombie[s],trial_id=401+i,source=source(zombie[s]),repeat=i+1) for i,s in enumerate('ABCAB')]}
for b in range(1,5):groups['batch' if b==1 else f'batch{b}']=[dict(t,trial_id=100*(b+4)+t['trial_id'],source=source(t),batch=b) for t in std['trials']]
for t in sum(groups.values(),[]):
    t.update(model=MODEL);t.pop('reasoning_effort',None)
    fn(f"trial/{t['trial_id']}",copy_setup(t['source'],t['trial_id']))
(OUT/'schedule.json').write_text(json.dumps(groups,indent=2)+'\n')
print('Built',{k:len(v) for k,v in groups.items()},'trial functions')
