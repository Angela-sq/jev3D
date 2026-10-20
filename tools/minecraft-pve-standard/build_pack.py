#!/usr/bin/env python3
"""Build evaluator-only reset/scoring datapack and the fixed schedule. No combat policy."""
import json,random,shutil
from config import OUT,SITES,REPEATS,SCHEDULE_SEED,CALIBRATION,MODEL,EFFORT
from core import MOBS
PACK=OUT/'datapack'
shutil.rmtree(PACK,ignore_errors=True)
F=PACK/'data/pve/function'
def fn(name,lines):
    p=F/(name+'.mcfunction');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(lines)+'\n')
def obj(name,criterion='dummy'):return f'scoreboard objectives add {name} {criterion}'
F.mkdir(parents=True)
(PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'Standard PvE evaluator','pack_format':121,'min_format':121,'max_format':121}}))
for tag in ['load','tick']:
    p=PACK/f'data/minecraft/tags/function/{tag}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'values':['pve:'+tag]}))
# Hostile types removed if they appear untagged during a fight (none should: spawning is off).
HOSTILE=MOBS+['drowned','zombie_villager','bogged','parched','slime','phantom','enderman','silverfish','endermite','evoker','vex','ravager','illusioner','breeze','creaking','zombified_piglin','piglin','piglin_brute','hoglin','zoglin','magma_cube','blaze','ghast','wither_skeleton','guardian','elder_guardian','shulker','warden']
p=PACK/'data/pve/tags/entity_type/hostile.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'values':[{'id':'minecraft:'+m,'required':False} for m in HOSTILE]}))
KILL=[f'pve_k{i}' for i in range(len(MOBS))]
fn('load',[obj('pve'),obj('pve_death','deathCount'),obj('pve_kills'),*[obj(k,f'minecraft.killed:minecraft.{m}') for k,m in zip(KILL,MOBS)],obj('pve_taken','minecraft.custom:minecraft.damage_taken'),obj('pve_dealt','minecraft.custom:minecraft.damage_dealt'),
'scoreboard players set #phase pve 0','difficulty normal',
*[f'gamerule minecraft:{g} false' for g in ['spawn_mobs','spawn_monsters','spawn_patrols','spawn_wandering_traders','spawn_phantoms','advance_time','advance_weather','natural_health_regeneration','mob_griefing','send_command_feedback','show_advancement_messages']],
'gamerule minecraft:immediate_respawn true','gamerule minecraft:keep_inventory true','time set noon','weather clear','forceload add 192 -288 288 -176','worldborder damage amount 0','worldborder damage buffer 0','tellraw @a "PVE evaluator loaded"'])
fn('tick',[
'execute if score #phase pve matches 1 run scoreboard players remove #countdown pve 1',
'execute if score #phase pve matches 1 if score #countdown pve matches ..0 run function pve:begin',
'execute if score #phase pve matches 2 run function pve:active',
])
# Order decides same-tick ties: death, then win, then target lost, then timeout.
fn('active',[
'scoreboard players add #ticks pve 1',
*[f'execute if score #mob pve matches {i} run scoreboard players operation @a pve_kills = @a {k}' for i,k in enumerate(KILL)],
'execute store result score #hp pve run data get entity @p Health 100',
'execute store result score #n pve if entity @e[type=#pve:hostile,tag=!pve_enemy]',
'scoreboard players operation #intruders pve += #n pve',
'kill @e[type=#pve:hostile,tag=!pve_enemy]',
'execute as @e[tag=pve_enemy] at @s unless entity @a[distance=..30] run scoreboard players set #escaped pve 1',
'execute if score #phase pve matches 2 if entity @a[scores={pve_death=1..}] run function pve:end/death',
'execute if score #phase pve matches 2 if score @p pve_kills >= #target pve run function pve:end/win',
'execute if score #phase pve matches 2 unless entity @e[tag=pve_enemy] run function pve:end/target_lost',
'execute if score #phase pve matches 2 if score #ticks pve matches 1800.. run function pve:end/timeout',
])
fn('begin',['execute at @p run kill @e[type=!player,tag=!pve_enemy,distance=..80]','effect clear @a','execute if score #night pve matches 1 run effect give @a night_vision infinite 0 true','gamemode adventure @a','scoreboard players set #ticks pve 0','scoreboard players set #phase pve 2','execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:0b}','title @a times 0 15 5','title @a title "FIGHT"','tellraw @a ["PVE_START|",{"score":{"name":"#id","objective":"pve"}}]'])
for outcome,num in [('win',1),('death',2),('timeout',3),('technical',4),('target_lost',5)]:
    fields=[('#id','pve'),('#outcome','pve'),('#ticks','pve'),('#hp','pve'),('@p','pve_kills'),('@p','pve_taken'),('@p','pve_dealt'),('#escaped','pve'),('#intruders','pve')]
    parts=['PVE_END|']
    for i,(name,ob) in enumerate(fields):
        if i:parts.append('|')
        parts.append({'score':{'name':name,'objective':ob}})
    fn('end/'+outcome,['scoreboard players set #phase pve 3',f'scoreboard players set #outcome pve {num}', ('scoreboard players set #hp pve 0' if outcome=='death' else '# preserve terminal health'),'tellraw @a '+json.dumps(parts,separators=(',',':')),'gamemode creative @a','execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:1b}','title @a times 0 200 0','title @a title '+json.dumps('TRIAL END: '+outcome.upper())])
SUN_BURNING={'zombie','skeleton','stray'}
# Amendment 1: spiders are neutral in daylight, so their fights run at midnight with player night vision.
NIGHT={'spider','cave_spider'}
WEAPON={'skeleton':'bow','stray':'bow','pillager':'crossbow','vindicator':'iron_axe'}
def setup(n,mob,site):
    s=next(x for x in SITES if x['site']==site);x,z=s['x'],s['z']
    lines=['scoreboard players set #phase pve 0','time set '+('midnight' if mob in NIGHT else 'noon'),f'scoreboard players set #night pve {int(mob in NIGHT)}','gamemode spectator @a','worldborder set 59999968',
           f'execute positioned {x} 100 {z} run kill @e[type=!player,distance=..80]',
           f'execute positioned {x} 100 {z} positioned over motion_blocking_no_leaves run tp @a ~ ~1 ~ 0 0',
           f'worldborder center {x} {z}','worldborder set 40','worldborder warning distance 0',
           'gamemode creative @a','effect clear @a','effect give @a instant_health 1 10 true','effect give @a saturation 1 10 true','clear @a',
           'item replace entity @a weapon.mainhand with iron_sword','item replace entity @a weapon.offhand with shield']
    for slot,item in [('head','helmet'),('chest','chestplate'),('legs','leggings'),('feet','boots')]:lines.append(f'item replace entity @a armor.{slot} with iron_{item}')
    for ob in ['pve_death','pve_kills',*KILL,'pve_taken','pve_dealt']:lines.append(f'scoreboard players set @a {ob} 0')
    lines.append(f'execute positioned {x} 100 {z+8} positioned over motion_blocking run summon {mob} ~ ~1 ~ {{Tags:["pve_enemy"],NoAI:1b,PersistenceRequired:1b,IsBaby:0b,CanPickUpLoot:0b,Rotation:[180f,0f]}}')
    for slot in ['weapon.mainhand','weapon.offhand','armor.head','armor.chest','armor.legs','armor.feet']:
        item=WEAPON.get(mob,'air') if slot=='weapon.mainhand' else 'leather_helmet[unbreakable={}]' if slot=='armor.head' and mob in SUN_BURNING else 'air'
        lines.append(f'item replace entity @e[tag=pve_enemy] {slot} with {item}')
    lines+=['effect clear @e[tag=pve_enemy]','execute at @p run spawnpoint @a ~ ~ ~',f'scoreboard players set #id pve {n}',f'scoreboard players set #mob pve {MOBS.index(mob)}','scoreboard players set #target pve 1',
            'scoreboard players set #ticks pve 0','scoreboard players set #hp pve 2000','scoreboard players set #escaped pve 0','scoreboard players set #intruders pve 0',
            'scoreboard players set #countdown pve 100','scoreboard players set #phase pve 1','title @a times 0 40 10','title @a title "Get ready"']
    return lines
trials=[]
for i,mob in enumerate(MOBS):
    for r in range(REPEATS):trials.append({'mob':mob,'site':SITES[(i+r)%len(SITES)]['site'],'repeat':r+1,'scored':True})
random.Random(SCHEDULE_SEED).shuffle(trials)
for n,t in enumerate(trials,1):t['trial_id']=n
# Pre-registered single rerun for a technical failure: ID 100+n, same condition.
reruns=[dict(t,trial_id=100+t['trial_id'],rerun_of=t['trial_id']) for t in trials]
# Amendment 1 trials: ID 200+n replaces spider/cave_spider trial n; 300+n is its single technical rerun.
amendments=[dict(t,trial_id=200+t['trial_id'],amends=t['trial_id']) for t in trials if t['mob'] in NIGHT]
amendments+=[dict(t,trial_id=100+t['trial_id'],rerun_of=t['trial_id']) for t in amendments]
for t in trials+reruns+amendments+CALIBRATION:
    t.update(model=MODEL,reasoning_effort=EFFORT)
    fn(f"trial/{t['trial_id']}",setup(t['trial_id'],t['mob'],t['site']))
# Evaluator-only validation setups: one per mob and site, negative IDs.
for i,mob in enumerate(MOBS):
    for j,s in enumerate(SITES):fn(f"validate/{mob}_{s['site'].lower()}",setup(-(100+10*i+j),mob,s['site']))
# Evaluator-only forced-outcome tests (validation; never used in scored trials).
fn('test/win',['damage @e[tag=pve_enemy,limit=1] 1000 minecraft:player_attack by @p'])
fn('test/lost',['kill @e[tag=pve_enemy]'])
fn('test/die',['kill @p'])
fn('test/win_and_die',['damage @e[tag=pve_enemy,limit=1] 1000 minecraft:player_attack by @p','kill @p'])
fn('test/lost_and_die',['kill @e[tag=pve_enemy]','kill @p'])
fn('test/invulnerable',['effect give @p resistance 120 4 true'])
fn('test/inspect',['tellraw @a ["PVE_INSPECT|mob|",{"nbt":"id","entity":"@e[tag=pve_enemy,limit=1]"},"|pos|",{"nbt":"Pos","entity":"@e[tag=pve_enemy,limit=1]"},"|player|",{"nbt":"Pos","entity":"@p"},"|equipment|",{"nbt":"equipment","entity":"@e[tag=pve_enemy,limit=1]"},"|effects|",{"nbt":"active_effects","entity":"@e[tag=pve_enemy,limit=1]"},"|health|",{"nbt":"Health","entity":"@e[tag=pve_enemy,limit=1]"},"|count|",{"score":{"name":"#n","objective":"pve"}}]',
    'execute store result score #n pve if entity @e[tag=pve_enemy]',
    'tellraw @a ["PVE_COUNT|",{"score":{"name":"#n","objective":"pve"}},"|others|"]',
    'execute store result score #n pve if entity @e[type=!player,tag=!pve_enemy,distance=..80]',
    'tellraw @a ["PVE_OTHERS|",{"score":{"name":"#n","objective":"pve"}}]'])
(OUT/'schedule.json').write_text(json.dumps({'schedule_seed':SCHEDULE_SEED,'sites':SITES,'mobs':MOBS,'trials':trials,'reruns':reruns,'amendments':amendments,'calibration':CALIBRATION},indent=2)+'\n')
print('Built',len(trials),'scored and',len(CALIBRATION),'calibration trial functions')
