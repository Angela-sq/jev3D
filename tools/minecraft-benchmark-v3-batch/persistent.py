"""Input state transitions only; no game-state reads or combat policy."""
def expired(state, now_ns):
    return bool(state) and now_ns >= state['expires_ns']
def transition(previous, desired, run):
    oldkeys=set(previous.get('keys',[]));newkeys=set(desired.get('keys',[]))
    oldbuttons=set(previous.get('buttons',[]));newbuttons=set(desired.get('buttons',[]))
    for key in sorted(oldkeys-newkeys):run('xdotool','keyup',key)
    for button in sorted(oldbuttons-newbuttons):run('xdotool','mouseup',str(button))
    for key in sorted(newkeys-oldkeys):run('xdotool','keydown',key)
    for button in sorted(newbuttons-oldbuttons):run('xdotool','mousedown',str(button))
