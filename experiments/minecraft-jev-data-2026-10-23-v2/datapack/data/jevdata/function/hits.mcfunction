scoreboard players operation #dealt jev = @p pve_dealt
scoreboard players operation #taken jev = @p pve_taken
execute unless score #dealt jev = #pdealt jev run function jevdata:emit
execute unless score #taken jev = #ptaken jev run function jevdata:emit
