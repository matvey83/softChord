
from __pyjamas__ import JS

# a dictionary of module override names (platform-specific)
overrides = None # to be updated by app, on compile

# the remote path for loading modules
loadpath = None

stacktrace = None

appname = None

def setloadpath(lp):
    global loadpath
    loadpath = lp

def setappname(an):
    global appname
    appname = an

def getloadpath():
    return loadpath

def addoverride(module_name, path):
    overrides[module_name] = path

def exc_info():
    le = JS('$pyjs.__last_exception__')
    if not le:
        return (None, None, None)
    if not hasattr(le.error, '__class__'):
        cls = None
    else:
        cls = le.error.__class__
    return (cls, le.error, None)

def exc_clear():
    JS('$pyjs.__last_exception__ = null;')

# save_exception_stack is totally javascript, to prevent trackstack pollution
JS("""sys.save_exception_stack = function () {
    var save_stack = [];
    for (var needle in $pyjs.trackstack) {
        var t = new Object();
        for (var p in $pyjs.trackstack[needle]) {
            t[p] = $pyjs.trackstack[needle][p];
        }
        save_stack.push(t);
        $pyjs.__last_exception_stack__ = save_stack;
    }
return null;
};""")

def trackstackstr(stack=None):
    if stack is None:
        stack = JS('$pyjs.__last_exception_stack__')
    if not stack:
        return ''
    stackstrings = []
    msg = ''
    for s in list(stack):
        JS("msg = eval(s.module + '.__track_lines__[' + s.lineno + ']');")
        if msg:
            stackstrings.append(msg)
        else:
            stackstrings.append('%s.py, line %d' % (s.module, s.lineno))
    return '\n'.join(stackstrings)

platform = JS('$pyjs.platform')
byteorder = 'little' # Needed in struct.py, assume all systems are little endian and not big endian
maxint = 2147483647  # javascript bit operations are on 32 bit signed numbers
