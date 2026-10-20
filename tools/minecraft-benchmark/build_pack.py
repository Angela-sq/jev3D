#!/usr/bin/env python3
"""Build evaluator-only reset/scoring datapack. No combat policy."""
import json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'experiments/minecraft-pve-2026-10-19'
PACK=OUT/'datapack'
F=PACK/'data/pve/function'
F.mkdir(parents=True,exist_ok=True)
def fn(name,lines):
    p=F/(name+'.mcfunction');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(lines)+'\n')
def obj(name,criterion='dummy'):return f'scoreboard objectives add {name} {criterion}'
(PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'Natural PvE evaluator v1','pack_format':121,'min_format':121,'max_format':121}}))
for tag in ['load','tick']:
    p=PACK/f'data/minecraft/tags/function/{tag}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'values':['pve:'+tag]}))
fn('load',[obj('pve'),obj('pve_death','deathCount'),obj('pve_kills'),obj('pve_z','minecraft.killed:minecraft.zombie'),obj('pve_s','minecraft.killed:minecraft.skeleton'),obj('pve_taken','minecraft.custom:minecraft.damage_taken'),obj('pve_dealt','minecraft.custom:minecraft.damage_dealt'),
'scoreboard players set #phase pve 0','difficulty normal','gamerule minecraft:spawn_mobs false','gamerule minecraft:advance_time false','gamerule minecraft:advance_weather false','gamerule minecraft:natural_health_regeneration false','gamerule minecraft:mob_griefing false','gamerule minecraft:immediate_respawn true','gamerule minecraft:keep_inventory true','gamerule minecraft:send_command_feedback false','gamerule minecraft:show_advancement_messages false','time set noon','weather clear','forceload add 192 -288 288 -176','tellraw @a "PVE evaluator loaded"'])
fn('tick',[
'execute if score #phase pve matches 1 run scoreboard players remove #countdown pve 1',
'execute if score #phase pve matches 1 if score #countdown pve matches ..0 run function pve:begin',
'execute if score #phase pve matches 2 run function pve:active',
])
fn('active',[
'scoreboard players add #ticks pve 1','scoreboard players operation @a pve_kills = @a pve_z','scoreboard players operation @a pve_kills += @a pve_s',
'execute store result score #hp pve run data get entity @p Health 100',
'execute if score #phase pve matches 2 if entity @a[scores={pve_death=1..}] run function pve:end/death',
'execute if score #phase pve matches 2 if score @p pve_kills >= #target pve run function pve:end/win',
'execute if score #phase pve matches 2 if score #ticks pve matches 1800.. run function pve:end/timeout',
])
fn('begin',['effect clear @a','gamemode adventure @a','scoreboard players set #ticks pve 0','scoreboard players set #phase pve 2','execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:0b}', 'title @a times 0 15 5','title @a title "FIGHT"','tellraw @a ["PVE_START|",{"score":{"name":"#id","objective":"pve"}}]'])
for outcome,num in [('win',1),('death',2),('timeout',3),('technical',4)]:
    fields=[('#id','pve'),('#outcome','pve'),('#ticks','pve'),('#hp','pve'),('@p','pve_kills'),('@p','pve_taken'),('@p','pve_dealt')]
    parts=['PVE_END|']
    for i,(name,ob) in enumerate(fields):
        if i:parts.append('|')
        parts.append({'score':{'name':name,'objective':ob}})
    fn('end/'+outcome,['scoreboard players set #phase pve 3',f'scoreboard players set #outcome pve {num}', ('scoreboard players set #hp pve 0' if outcome=='death' else '# preserve terminal health'),'tellraw @a '+json.dumps(parts,separators=(',',':')),'gamemode creative @a','execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:1b}','title @a times 0 200 0','title @a title '+json.dumps('TRIAL END: '+outcome.upper())])
SITES=[{'site':'A','x':240.5,'z':-240.5,'description':'grassland terrace'}, {'site':'B','x':270.5,'z':-210.5,'description':'grassland slope'}, {'site':'C','x':215.5,'z':-190.5,'description':'grassland edge'}]
trials=[{'site':s['site'],'encounter':e,'repeat':r,'scored':True} for r in range(1,5) for s in SITES for e in ['zombie','two_zombies','skeleton']]
random.Random(20261019).shuffle(trials)
trials=[dict(site='A',encounter=e,repeat=0,scored=False) for e in ['zombie','two_zombies','skeleton']]+trials
for n,t in enumerate(trials,1):
    t['trial_id']=n;t['model']='gpt-6-astra';t['reasoning_effort']='medium'
    s=next(s for s in SITES if s['site']==t['site']); x,z=s['x'],s['z']
    mob='skeleton' if t['encounter']=='skeleton' else 'zombie'; count=2 if t['encounter']=='two_zombies' else 1
    lines=['scoreboard players set #phase pve 0','gamemode spectator @a','worldborder set 59999968','kill @e[tag=pve_enemy]','kill @e[type=item]','kill @e[type=arrow]',f'execute positioned {x} 100 {z} positioned over motion_blocking_no_leaves run tp @a ~ ~1 ~ 0 0',f'worldborder center {x} {z}','worldborder set 40','worldborder warning distance 0','gamemode creative @a','effect clear @a','effect give @a instant_health 1 10 true','effect give @a saturation 1 10 true','clear @a','item replace entity @a weapon.mainhand with iron_sword','item replace entity @a weapon.offhand with shield']
    for slot,item in [('head','helmet'),('chest','chestplate'),('legs','leggings'),('feet','boots')]:lines.append(f'item replace entity @a armor.{slot} with iron_{item}')
    for ob in ['pve_death','pve_kills','pve_z','pve_s','pve_taken','pve_dealt']:lines.append(f'scoreboard players set @a {ob} 0')
    for i in range(count):
        mx=x+(-3 if count==2 and i==0 else 3 if count==2 else 0);mz=z+8
        lines.append(f'execute positioned {mx} 100 {mz} positioned over motion_blocking run summon {mob} ~ ~1 ~ {{Tags:["pve_enemy"],NoAI:1b,PersistenceRequired:1b,IsBaby:0b,CanPickUpLoot:0b}}')
    lines+=['item replace entity @e[tag=pve_enemy] armor.head with leather_helmet[unbreakable={}]']
    if mob=='skeleton':lines+=['item replace entity @e[tag=pve_enemy] weapon.mainhand with bow']
    lines+=['execute at @p run spawnpoint @a ~ ~ ~',f'scoreboard players set #id pve {n}',f'scoreboard players set #target pve {count}','scoreboard players set #ticks pve 0','scoreboard players set #hp pve 2000','scoreboard players set #countdown pve 100','scoreboard players set #phase pve 1','title @a times 0 40 10','title @a title "Get ready"']
    fn(f'trial/{n}',lines)
(OUT/'schedule.json').write_text(json.dumps({'seed':-6257074856933950438,'schedule_seed':20261019,'sites':SITES,'trials':trials},indent=2)+'\n')
print('Built',len(trials),'trial functions')
