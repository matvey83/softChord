from __pyjamas__ import JS


class EventDelegate:
    """
    Create the equivalent of a bound method.  This also prepends extra
    args, if any, to the called method's argument list when it calls it.

    Pass the method name you want to implement (javascript doesn't
    support callables).

    @type args: list
    @param args: If given, the arguments will be prepended to the
                 arguments passed to the event callback
    """
    def __init__(self, eventMethodName, obj, method, *args):
        self.obj = obj
        self.method = method
        self.args = args
        JS("this[eventMethodName] = this.onEvent;")

    def onEvent(self, *args):
        self.method.apply(self.obj, self.args.l.concat(args.l))

