scoreboard objectives add pve dummy
scoreboard objectives add pve_death deathCount
scoreboard objectives add pve_kills dummy
scoreboard objectives add pve_k0 minecraft.killed:minecraft.zombie
scoreboard objectives add pve_k1 minecraft.killed:minecraft.husk
scoreboard objectives add pve_k2 minecraft.killed:minecraft.skeleton
scoreboard objectives add pve_k3 minecraft.killed:minecraft.stray
scoreboard objectives add pve_k4 minecraft.killed:minecraft.spider
scoreboard objectives add pve_k5 minecraft.killed:minecraft.cave_spider
scoreboard objectives add pve_k6 minecraft.killed:minecraft.creeper
scoreboard objectives add pve_k7 minecraft.killed:minecraft.witch
scoreboard objectives add pve_k8 minecraft.killed:minecraft.pillager
scoreboard objectives add pve_k9 minecraft.killed:minecraft.vindicator
scoreboard objectives add pve_taken minecraft.custom:minecraft.damage_taken
scoreboard objectives add pve_dealt minecraft.custom:minecraft.damage_dealt
scoreboard players set #phase pve 0
difficulty normal
gamerule minecraft:spawn_mobs false
gamerule minecraft:spawn_monsters false
gamerule minecraft:spawn_patrols false
gamerule minecraft:spawn_wandering_traders false
gamerule minecraft:spawn_phantoms false
gamerule minecraft:advance_time false
gamerule minecraft:advance_weather false
gamerule minecraft:natural_health_regeneration false
gamerule minecraft:mob_griefing false
gamerule minecraft:send_command_feedback false
gamerule minecraft:show_advancement_messages false
gamerule minecraft:immediate_respawn true
gamerule minecraft:keep_inventory true
time set noon
weather clear
forceload add 192 -288 288 -176
worldborder damage amount 0
worldborder damage buffer 0
tellraw @a "PVE evaluator loaded"
