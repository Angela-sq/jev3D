"""v5: after v4 on the dev fights (5/10). The aim was the problem, not the moves:
  - witch: 80 swings, 0 damage; the video shows the crosshair in the sky above her. skeleton, stray: the yaw error
    swung by +-30 to 70 degrees. The state comes a few ticks late, so the body kept turning after it had turned
    enough, and v4's faster turning made it worse. Now the body adds the mouse moves it has sent but the state cannot
    show yet (Smith predictor, 0.08 s) and turns by half the remaining error each tick; no fast turning.
  - Everything else is v4 (swing only on target, aim 2 ticks ahead, the creeper guard, moves by distance and mob)."""
from harness.v4 import INTERVAL,QUESTION,TACTICS,MOVES,view,options,describe,adjust as v4_adjust

def adjust(tac,s,g,body):
    tac=v4_adjust(tac,s,g,body)
    tac.update(lead=2,fast_aim=False,predict_aim=0.08,aim_gain=.5)
    return tac
