# FocusImplOld

def blur(elem):
    JS("""
    // Attempts to blur elements from within an event callback will
    // generally be unsuccessful, so we invoke blur() from outside of
    // the callback.
    $wnd.setTimeout(function() {
                                   elem.firstChild.blur();
                    },
                    0);
    """)

def createFocusable():
    JS("""
    var div = $doc.createElement('div');
    var input = $doc.createElement('input');
    input.type = 'text';
    input.style.opacity = 0;
    input.style.zIndex = -1;
    input.style.width = '1px';
    input.style.height = '1px';
    input.style.overflow = 'hidden';
    input.style.position = 'absolute';

    input.addEventListener( 'blur',
                        function(evt)
                        {
                            if (this.parentNode.onblur)
                                this.parentNode.onblur(evt);
                        },
                        false);

    input.addEventListener( 'focus',
                    function(evt)
                    {
                        if (this.parentNode.onfocus)
                            this.parentNode.onfocus(evt);
                    },
                    false);

    div.addEventListener(
                        'mousedown',
                        function(evt) { this.firstChild.focus(); },
                        false);

    div.appendChild(input);
    return div;
    """)

def focus(elem):
    JS("""
    // Attempts to focus elements from within an event callback will
    // generally be unsuccessful, so we invoke focus() from outside of
    // the callback.
    $wnd.setTimeout(function() {
                                   elem.firstChild.focus();
                    },
                    0);
    """)

def getTabIndex(elem):
    JS("""
    return elem.firstChild.tabIndex;
    """)

def setAccessKey(elem, key):
    JS("""
    if (elem.firstChild != null) elem.firstChild.accessKey = key;
    """)

def setTabIndex(elem, index):
    JS("""
    if (elem.firstChild != null) elem.firstChild.tabIndex = index;
    """)


