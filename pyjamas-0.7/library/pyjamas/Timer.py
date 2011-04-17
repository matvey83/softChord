# This is the gtk-dependent Timer module.
# For the pyjamas/javascript version, see platform/TimerPyJS.py

import sys
from __pyjamas__ import JS

global timeout_add
global timeout_end
timeout_add = None
timeout_end = None

# the following is needed because we are currently not able to override things
# except functions and classes
if sys.platform not in ['mozilla', 'ie6', 'opera', 'oldmoz', 'safari']:
    import pyjd

global timers
timers = None


def set_timer(interval, fn):
    pass


def kill_timer(timer):
    pass


def init():
    global timers
    timers = []

init()


class Timer:

    def __init__(self, time, notify):
        if hasattr(notify, "onTimer"):
            self.notify_fn = notify.onTimer
        else:
            self.notify_fn = notify
        self.timer_id = timeout_add(time, self.notify)

    def clearInterval(self, timer_id):
        pass

    def clearTimeout(self, timer_id):
        pass

    def createInterval(self, timer, period):
        pass

    def createTimeout(self, timer, delay):
        pass

    # TODO - requires Window.addWindowCloseListener
    def hookWindowClosing(self):
        pass

    def notify(self, *args):
        self._notify(*args)

    def _notify(self, *args):
        if not self.notify_fn:
            return False
        self.notify_fn(self.timer_id)
        return False

    def cancel(self):
        if not timeout_end:
            print "TODO: cancel timer", self.timer_id
            self.notify_fn = None # hmmm....
            return
        if self.timer_id is not None:
            timeout_end(self.timer_id)
            self.timer_id = None

    def run(self):
        pass

    def schedule(self, delayMillis):
        pass

    def scheduleRepeating(self, periodMillis):
        pass

    # TODO: UncaughtExceptionHandler, fireAndCatch
    def fire(self):
        pass

    def fireImpl(self):
        pass

    def getID(self):
        return self.timer_id
