scoreboard players operation #pdealt jevh = #dealt jevh
scoreboard players operation #ptaken jevh = #taken jevh
tellraw @a ["PVE_HIT|",{"score":{"name":"#id","objective":"pve"}},"|",{"score":{"name":"#ticks","objective":"pve"}},"|",{"score":{"name":"#hp","objective":"pve"}},"|",{"score":{"name":"#dealt","objective":"jevh"}},"|",{"score":{"name":"#taken","objective":"jevh"}}]
