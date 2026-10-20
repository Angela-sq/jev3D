scoreboard players set #phase pve 0
gamemode spectator @a
worldborder set 59999968
kill @e[tag=pve_enemy]
kill @e[type=item]
kill @e[type=arrow]
execute positioned 215.5 100 -190.5 positioned over motion_blocking_no_leaves run tp @a ~ ~1 ~ 0 0
worldborder center 215.5 -190.5
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
scoreboard players set @a pve_z 0
scoreboard players set @a pve_s 0
scoreboard players set @a pve_taken 0
scoreboard players set @a pve_dealt 0
execute positioned 212.5 100 -182.5 positioned over motion_blocking run summon zombie ~ ~1 ~ {Tags:["pve_enemy"],NoAI:1b,PersistenceRequired:1b,IsBaby:0b,CanPickUpLoot:0b}
execute positioned 218.5 100 -182.5 positioned over motion_blocking run summon zombie ~ ~1 ~ {Tags:["pve_enemy"],NoAI:1b,PersistenceRequired:1b,IsBaby:0b,CanPickUpLoot:0b}
item replace entity @e[tag=pve_enemy] armor.head with leather_helmet[unbreakable={}]
execute at @p run spawnpoint @a ~ ~ ~
scoreboard players set #id pve 35
scoreboard players set #target pve 2
scoreboard players set #ticks pve 0
scoreboard players set #hp pve 2000
scoreboard players set #countdown pve 100
scoreboard players set #phase pve 1
title @a times 0 40 10
title @a title "Get ready"
