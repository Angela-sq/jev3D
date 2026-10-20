scoreboard players set #phase pve 3
scoreboard players set #outcome pve 3
# preserve terminal health
tellraw @a ["PVE_END|",{"score":{"name":"#id","objective":"pve"}},"|",{"score":{"name":"#outcome","objective":"pve"}},"|",{"score":{"name":"#ticks","objective":"pve"}},"|",{"score":{"name":"#hp","objective":"pve"}},"|",{"score":{"name":"@p","objective":"pve_kills"}},"|",{"score":{"name":"@p","objective":"pve_taken"}},"|",{"score":{"name":"@p","objective":"pve_dealt"}}]
gamemode creative @a
execute as @e[tag=pve_enemy] run data merge entity @s {NoAI:1b}
title @a times 0 200 0
title @a title "TRIAL END: TIMEOUT"
