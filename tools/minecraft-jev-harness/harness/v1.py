"""v1: the first harness. Plain facts (distance, angle, health both ways, the sword's charge, recent hits) and the same
seven moves every time. The body aims at the mob in every move and swings only in `strike`."""
from harness.common import base_view

INTERVAL=0.2
QUESTION='Which move should the player make now to kill the mob without dying?'
TACTICS={
    'approach':dict(keys=['w']),
    'strike':dict(strike=True),
    'back_off':dict(keys=['s']),
    'strafe_left':dict(keys=['a']),
    'strafe_right':dict(keys=['d']),
    'shield':dict(shield=True),
    'wait':dict(),
}
MOVES={
    'approach':'Walk toward the mob.',
    'strike':'Swing the sword at the mob (only lands if the mob is within 3 blocks).',
    'back_off':'Walk backward, away from the mob.',
    'strafe_left':'Step sideways to the left while facing the mob.',
    'strafe_right':'Step sideways to the right while facing the mob.',
    'shield':'Raise the shield to block attacks (you cannot attack while it is up).',
    'wait':'Stand still and keep facing the mob.',
}

def view(s,g,body,hits,mem,history):return base_view(s,g,body,hits,mem,history)

def options(v):return dict(MOVES)

def describe(v):
    side='straight ahead' if abs(v['yaw_err'])<10 else f"{abs(v['yaw_err']):.0f} degrees to your {'right' if v['yaw_err']>0 else 'left'}"
    move='toward you' if v['closing']>.3 else 'away from you' if v['closing']<-.3 else 'neither closer nor farther'
    return '\n'.join([
        f"Minecraft fight. You hold an iron sword and a shield and wear iron armor. Goal: kill the {v['mob']} within 90 seconds without dying.",
        f"The {v['mob']} is {v['hdist']:.1f} blocks away, {side}. It is moving {move} ({abs(v['closing']):.1f} blocks/s).",
        f"Your health: {v['php']:.0f}/20. The {v['mob']}'s health: {v['mhp']:.0f}/{v['mhp_max']}.",
        f"Your sword is {'fully charged' if v['cool']>=.95 else 'recharging'}.",
        f"Last 3 seconds: you hit it {v['hits_dealt_3s']} times; it hit you {v['hits_taken_3s']} times.",
        f"Fight time: {v['t']:.0f} of 90 seconds. Your last move: {v['last'] or 'none'}."])
