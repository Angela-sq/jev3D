scoreboard players add #ticks pve 1
execute if score #mob pve matches 0 run scoreboard players operation @a pve_kills = @a pve_k0
execute if score #mob pve matches 1 run scoreboard players operation @a pve_kills = @a pve_k1
execute if score #mob pve matches 2 run scoreboard players operation @a pve_kills = @a pve_k2
execute if score #mob pve matches 3 run scoreboard players operation @a pve_kills = @a pve_k3
execute if score #mob pve matches 4 run scoreboard players operation @a pve_kills = @a pve_k4
execute if score #mob pve matches 5 run scoreboard players operation @a pve_kills = @a pve_k5
execute if score #mob pve matches 6 run scoreboard players operation @a pve_kills = @a pve_k6
execute if score #mob pve matches 7 run scoreboard players operation @a pve_kills = @a pve_k7
execute if score #mob pve matches 8 run scoreboard players operation @a pve_kills = @a pve_k8
execute if score #mob pve matches 9 run scoreboard players operation @a pve_kills = @a pve_k9
execute store result score #hp pve run data get entity @p Health 100
execute store result score #n pve if entity @e[type=#pve:hostile,tag=!pve_enemy]
scoreboard players operation #intruders pve += #n pve
kill @e[type=#pve:hostile,tag=!pve_enemy]
execute as @e[tag=pve_enemy] at @s unless entity @a[distance=..30] run scoreboard players set #escaped pve 1
execute if score #phase pve matches 2 if entity @a[scores={pve_death=1..}] run function pve:end/death
execute if score #phase pve matches 2 if score @p pve_kills >= #target pve run function pve:end/win
execute if score #phase pve matches 2 unless entity @e[tag=pve_enemy] run function pve:end/target_lost
execute if score #phase pve matches 2 if score #ticks pve matches 1800.. run function pve:end/timeout
