
def kill_timer(timer):
    timer.cancel()

def init():
    global timeout_add
    global timeout_end
    timeout_add = pyjd.gobject.timeout_add
    timeout_end = kill_timer

