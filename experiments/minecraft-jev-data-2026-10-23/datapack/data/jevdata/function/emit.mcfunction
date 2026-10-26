scoreboard players operation #pdealt jev = #dealt jev
scoreboard players operation #ptaken jev = #taken jev
tellraw @a ["PVE_HIT|",{"score":{"name":"#id","objective":"pve"}},"|",{"score":{"name":"#ticks","objective":"pve"}},"|",{"score":{"name":"#hp","objective":"pve"}},"|",{"score":{"name":"#dealt","objective":"jev"}},"|",{"score":{"name":"#taken","objective":"jev"}}]
