#!/usr/bin/env python3
"""Build the jevh datapack. Each setup copies a standard PvE setup without its trial ID (the runner sets #id first).
During the fight the pack prints the game state every tick (JH line) and every damage change (PVE_HIT).
Only the harness reads these lines; the scoring is the standard evaluator's, unchanged."""
import json,re,shutil
from config import OUT,STANDARD
PACK=OUT/'datapack'
SRC=STANDARD/'datapack/data/pve/function/trial'
shutil.rmtree(PACK,ignore_errors=True)
F=PACK/'data/jevh/function'
def fn(name,lines):
    p=F/(name+'.mcfunction');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(lines)+'\n')
F.mkdir(parents=True)
(PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'Jev harness state','pack_format':121,'min_format':121,'max_format':121}}))
for tag in ['load','tick']:
    p=PACK/f'data/minecraft/tags/function/{tag}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'values':['jevh:'+tag]}))
fn('load',['scoreboard objectives add jevh dummy','tellraw @a "JEVH pack loaded"'])
fn('tick',['execute if score #phase pve matches 2 at @p run function jevh:state','execute if score #phase pve matches 2..3 run function jevh:hits'])
P='@p';M='@e[tag=pve_enemy,limit=1,sort=nearest]'   # nearest to the player (state runs at @p)
def nbt(path,entity):return {'nbt':path,'entity':entity}
fn('state',['execute store result score #arrows jevh if entity @e[type=#minecraft:arrows,distance=..12,nbt={inGround:0b}]',
            'tellraw @a '+json.dumps(['JH|',{'score':{'name':'#id','objective':'pve'}},'|',{'score':{'name':'#ticks','objective':'pve'}},'|',{'score':{'name':'#mob','objective':'pve'}},
                                      '|',nbt('Pos',P),'|',nbt('Rotation',P),'|',nbt('Health',P),'|',nbt('HurtTime',P),'|',nbt('OnGround',P),
                                      '|',nbt('Pos',M),'|',nbt('Rotation',M),'|',nbt('Health',M),'|',nbt('HurtTime',M),'|',nbt('Motion',M),
                                      '|',{'score':{'name':'#arrows','objective':'jevh'}}],separators=(',',':'))])
fn('hits',['scoreboard players operation #dealt jevh = @p pve_dealt','scoreboard players operation #taken jevh = @p pve_taken',
           'execute unless score #dealt jevh = #pdealt jevh run function jevh:emit',
           'execute unless score #taken jevh = #ptaken jevh run function jevh:emit'])
fn('emit',['scoreboard players operation #pdealt jevh = #dealt jevh','scoreboard players operation #ptaken jevh = #taken jevh',
           'tellraw @a '+json.dumps(['PVE_HIT|',{'score':{'name':'#id','objective':'pve'}},'|',{'score':{'name':'#ticks','objective':'pve'}},'|',{'score':{'name':'#hp','objective':'pve'}},'|',{'score':{'name':'#dealt','objective':'jevh'}},'|',{'score':{'name':'#taken','objective':'jevh'}}],separators=(',',':'))])
std=json.loads((STANDARD/'schedule.json').read_text())
def source(t):
    """Standard trial whose setup a fight copies (spiders use their night-time amendment setup)."""
    return 200+t['trial_id'] if t['mob'] in ('spider','cave_spider') else t['trial_id']
for t in std['trials']:
    s=source(t);lines=(SRC/f'{s}.mcfunction').read_text().splitlines()
    out=[l for l in lines if not re.fullmatch(r'scoreboard players set #id pve -?\d+',l)]
    assert len(out)==len(lines)-1
    fn(f'setup/{s}',['scoreboard players set #pdealt jevh 0','scoreboard players set #ptaken jevh 0',*out])
print('Built',len(std['trials']),'setups')
