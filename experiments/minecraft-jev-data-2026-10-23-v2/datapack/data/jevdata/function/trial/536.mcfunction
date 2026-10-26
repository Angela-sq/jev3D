scoreboard players set #pdealt jev 0
scoreboard players set #ptaken jev 0
scoreboard players set #phase pve 0
time set noon
scoreboard players set #night pve 0
gamemode spectator @a
worldborder set 59999968
execute positioned 270.5 100 -210.5 run kill @e[type=!player,distance=..80]
execute positioned 270.5 100 -210.5 positioned over motion_blocking_no_leaves run tp @a ~ ~1 ~ 0 0
worldborder center 270.5 -210.5
worldborder set 40
worldborder warning distance 0
gamemode creative @a
effect clear @a
effect give @a instant_health 1 10 true
effect give @a saturation 1 10 true
clear @a
item replace entity @a weapon.mainhand with iron_sword
item replace entity @a weapon.offhand with shield
item replace entity @a armor.head with iron_helmet
item replace entity @a armor.chest with iron_chestplate
item replace entity @a armor.legs with iron_leggings
item replace entity @a armor.feet with iron_boots
scoreboard players set @a pve_death 0
scoreboard players set @a pve_kills 0
scoreboard players set @a pve_k0 0
scoreboard players set @a pve_k1 0
scoreboard players set @a pve_k2 0
scoreboard players set @a pve_k3 0
scoreboard players set @a pve_k4 0
scoreboard players set @a pve_k5 0
scoreboard players set @a pve_k6 0
scoreboard players set @a pve_k7 0
scoreboard players set @a pve_k8 0
scoreboard players set @a pve_k9 0
scoreboard players set @a pve_taken 0
scoreboard players set @a pve_dealt 0
execute positioned 270.5 100 -202.5 positioned over motion_blocking run summon pillager ~ ~1 ~ {Tags:["pve_enemy"],NoAI:1b,PersistenceRequired:1b,IsBaby:0b,CanPickUpLoot:0b,Rotation:[180f,0f]}
item replace entity @e[tag=pve_enemy] weapon.mainhand with crossbow
item replace entity @e[tag=pve_enemy] weapon.offhand with air
item replace entity @e[tag=pve_enemy] armor.head with air
item replace entity @e[tag=pve_enemy] armor.chest with air
item replace entity @e[tag=pve_enemy] armor.legs with air
item replace entity @e[tag=pve_enemy] armor.feet with air
effect clear @e[tag=pve_enemy]
execute at @p run spawnpoint @a ~ ~ ~
scoreboard players set #id pve 536
scoreboard players set #mob pve 8
scoreboard players set #target pve 1
scoreboard players set #ticks pve 0
scoreboard players set #hp pve 2000
scoreboard players set #escaped pve 0
scoreboard players set #intruders pve 0
scoreboard players set #countdown pve 100
scoreboard players set #phase pve 1
title @a times 0 40 10
title @a title "Get ready"
