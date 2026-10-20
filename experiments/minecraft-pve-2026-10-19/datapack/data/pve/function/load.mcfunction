scoreboard objectives add pve dummy
scoreboard objectives add pve_death deathCount
scoreboard objectives add pve_kills dummy
scoreboard objectives add pve_z minecraft.killed:minecraft.zombie
scoreboard objectives add pve_s minecraft.killed:minecraft.skeleton
scoreboard objectives add pve_taken minecraft.custom:minecraft.damage_taken
scoreboard objectives add pve_dealt minecraft.custom:minecraft.damage_dealt
scoreboard players set #phase pve 0
difficulty normal
gamerule minecraft:spawn_mobs false
gamerule minecraft:advance_time false
gamerule minecraft:advance_weather false
gamerule minecraft:natural_health_regeneration false
gamerule minecraft:mob_griefing false
gamerule minecraft:immediate_respawn true
gamerule minecraft:keep_inventory true
gamerule minecraft:send_command_feedback false
gamerule minecraft:show_advancement_messages false
time set noon
weather clear
forceload add 192 -288 288 -176
tellraw @a "PVE evaluator loaded"
