execute if score #phase pve matches 1 run scoreboard players remove #countdown pve 1
execute if score #phase pve matches 1 if score #countdown pve matches ..0 run function pve:begin
execute if score #phase pve matches 2 run function pve:active
