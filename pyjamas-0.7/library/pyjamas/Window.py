# This is the pyjd Window module.
# For the pyjamas/javascript version, see __browser__.pyjamas.Window

"""
    Window provides access to the DOM model's global Window.
"""

closingListeners = []
resizeListeners = []

from __pyjamas__ import JS, doc, wnd, get_main_frame
from pyjamas import Location

def init_listeners():
    pass

def addWindowCloseListener(listener):
    closingListeners.append(listener)

def addWindowResizeListener(listener):
    resizeListeners.append(listener)

def removeWindowCloseListener(listener):
    closingListeners.remove(listener)

def removeWindowResizeListener(listener):
    resizeListeners.remove(listener)

def alert(txt):
    get_main_frame()._alert(txt)

def confirm(msg):
    return wnd().confirm(msg)

def prompt(msg, defaultReply=""):
    return wnd().prompt(msg, defaultReply)

def enableScrolling(enable):
    doc().body.style.overflow = enable and 'auto' or 'hidden'

def scrollBy(x, y):
    wnd().scrollBy(x, y)

def scroll(x, y):
    wnd().scroll(x, y)

def getClientHeight():
    try:
        return wnd().innerHeight
    except:
        return doc().body.clientHeight;

def getClientWidth():
    try:
        return wnd().innerWidth
    except:
        return doc().body.clientWidth;

def getScrollLeft():
     return getDocumentRoot().scrollLeft;

def getScrollTop():
     return getDocumentRoot().scrollTop;

def getDocumentRoot():
    if doc().compatMode == 'CSS1Compat':
        return doc().documentElement
    return doc().body

def setLocation(url):
    w = wnd()
    w.location = url

location = None

def getLocation():
    global location
    if not location:
        location = Location.Location(wnd().location)
    return location
 
def getTitle():
    return doc().title

def open(url, name, features):
    wnd().open(url, name, features)

def setMargin(size):
    doc().body.style.margin = size;

def setTitle(title):
    d = doc()
    d.title = title

def setOnError(onError):
    pass

def onError(msg, url, linenumber):
    pass

# TODO: call fireClosedAndCatch
def onClosed():
    fireClosedImpl()

# TODO: call fireClosingAndCatch
def onClosing():
    fireClosingImpl()

# TODO: call fireResizedAndCatch
def onResize():
    fireResizedImpl()

def fireClosedAndCatch(handler):
    # FIXME - need implementation
    pass

def fireClosedImpl():
    for listener in closingListeners:
        listener.onWindowClosed()

def fireClosingAndCatch(handler):
    # FIXME - need implementation
    pass

def resize(width, height):
    """ changes size to specified width and height
    """
    wnd().resizeTo(width, height)

def resizeBy(width, height):
    """ changes size by specified width and height
    """
    wnd().resizeBy(width, height)

def fireClosingImpl():
    ret = None
    for listener in closingListeners:
        msg = listener.onWindowClosing()
        if ret is None:
            ret = msg
    return ret

def fireResizedAndCatch(handler):
    # FIXME - need implementation
    pass

def fireResizedImpl():
    for listener in resizeListeners:
        listener.onWindowResized(getClientWidth(), getClientHeight())

def init():
    pass

init()

