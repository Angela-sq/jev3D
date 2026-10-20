scoreboard players add #ticks pve 1
scoreboard players operation @a pve_kills = @a pve_z
scoreboard players operation @a pve_kills += @a pve_s
execute store result score #hp pve run data get entity @p Health 100
execute if score #phase pve matches 2 if entity @a[scores={pve_death=1..}] run function pve:end/death
execute if score #phase pve matches 2 if score @p pve_kills >= #target pve run function pve:end/win
execute if score #phase pve matches 2 if score #ticks pve matches 1800.. run function pve:end/timeout
