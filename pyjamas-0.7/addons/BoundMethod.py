from __pyjamas__ import JS


def BoundMethod(obj, method):
    """
    Return a javascript-compatible callable which can be used as a
    "bound method".

    Javascript doesn't support callables, and it doesn't support bound
    methods, so you can't use those in pyjamas currently.

    This is an OK workaround.
    """
    JS("""
        return function() {
            return method.apply(obj, arguments);
        };
    """)
