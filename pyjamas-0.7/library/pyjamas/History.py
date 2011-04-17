# This is the gtk-dependent History module.
# For the pyjamas/javascript version, see platform/HistoryPyJS.py

import sys
from __pyjamas__ import JS, doc, wnd
if sys.platform not in ['mozilla', 'ie6', 'opera', 'oldmoz', 'safari']:
    from __pyjamas__ import get_main_frame

global historyToken
historyToken = ''

historyListeners = []


"""
    Simple History management class for back/forward button support.

    This class allows your AJAX application to use a history.  Each time you
    call newItem(), a new item is added to the history and the history
    listeners are notified.  If the user clicks the browser's forward or back
    buttons, the appropriate item (a string passed to newItem) is fetched
    from the history and the history listeners are notified.

    The address bar of the browser contains the current token, using
    the "#" seperator (for implementation reasons, not because we love
    the # mark).

    You may want to check whether the hash already contains a history
    token when the page loads and use that to show appropriate content;
    this allows users of the site to store direct links in their
    bookmarks or send them in emails.

    To make this work properly in all browsers, you must add a specially
    named iframe to your html page, like this:

    <iframe id='__pygwt_historyFrame' style='width:0;height:0;border:0' />
"""


def addHistoryListener(listener):
    historyListeners.append(listener)


def back():
    wnd().history.back()


def forward():
    wnd().history.forward()


def getToken():
    global historyToken
    return historyToken


def newItem(ht):
    print "History - new item", ht
    onHistoryChanged(ht)
    return

    JS("""
    if(historyToken == "" || historyToken == null){
        historyToken = "#";
    }
    $wnd.location.hash = encodeURIComponent(historyToken);
    """)


# TODO - fireHistoryChangedAndCatch not implemented
def onHistoryChanged(ht):
    #UncaughtExceptionHandler handler = GWT.getUncaughtExceptionHandler();
    #if (handler != null)
    #   fireHistoryChangedAndCatch(historyToken, handler);
    #else
    fireHistoryChangedImpl(ht)


# TODO
def fireHistoryChangedAndCatch():
    pass


def fireHistoryChangedImpl(ht):
    for listener in historyListeners:
        listener.onHistoryChanged(ht)


def removeHistoryListener(listener):
    historyListeners.remove(listener)


def init():
    print "history: TODO"
    global historyToken
    historyToken = ''
    onHistoryChanged(historyToken)
    return
    JS("""
    $wnd.__historyToken = '';

    // Get the initial token from the url's hash component.
    var hash = $wnd.location.hash;
    if (hash.length > 0)
        $wnd.__historyToken = decodeURIComponent(hash.substring(1));

    // Create the timer that checks the browser's url hash every 1/4 s.
    $wnd.__checkHistory = function() {
        var token = '', hash = $wnd.location.hash;
        if (hash.length > 0)
            token = decodeURIComponent(hash.substring(1));

        if (token != $wnd.__historyToken) {
            $wnd.__historyToken = token;
            // TODO - move init back into History
            // this.onHistoryChanged(token);
            var h = new __History_History();
            h.onHistoryChanged(token);
        }

        $wnd.setTimeout('__checkHistory()', 250);
    };

    // Kick off the timer.
    $wnd.__checkHistory();

    return true;
    """)


init()
