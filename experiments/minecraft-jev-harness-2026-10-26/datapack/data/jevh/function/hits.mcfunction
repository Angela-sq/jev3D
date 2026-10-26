scoreboard players operation #dealt jevh = @p pve_dealt
scoreboard players operation #taken jevh = @p pve_taken
execute unless score #dealt jevh = #pdealt jevh run function jevh:emit
execute unless score #taken jevh = #ptaken jevh run function jevh:emit
