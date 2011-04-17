# to avoid using pywin32 timer module, we create a separate thread
# using threading.Timer.  unfortunately, python threads bollox up
# the COM stuff, so it is necessary to use PostMessage to notify
# the main window thread (to get it to wake up), after adding
# the timer function into a queue.  the queue probably isn't thread-safe -
# but i don't care!

def set_timer(interval, fn):
    t = pyjd.threading.Timer(interval / 1000.0, fn)
    t.start()
    return t

def kill_timer(timer):
    timer.cancel()

def init():
    global timeout_add
    global timeout_end
    timeout_add = set_timer
    timeout_end = kill_timer

class Timer:
    def notify(self, *args):
        pyjd.add_timer_queue(self._notify)

