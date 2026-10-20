execute at @p run kill @e[type=!player,tag=!pve_enemy,distance=..80]
effect clear @a
execute if score #night pve matches 1 run effect give @a night_vision infinite 0 true
gamemode adventure @a
scoreboard players set #ticks pve 0
scoreboard players set #phase pve 2
execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:0b}
title @a times 0 15 5
title @a title "FIGHT"
tellraw @a ["PVE_START|",{"score":{"name":"#id","objective":"pve"}}]
