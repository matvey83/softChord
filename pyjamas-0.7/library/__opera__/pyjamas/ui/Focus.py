# FocusImplOld

def blur(elem):
    JS("""
    elem.blur();
    """)

def createFocusable():
    JS("""
    var div = $doc.createElement('div');
    var input = $doc.createElement('input');
    input.type = 'text';
    input.style.width = input.style.height = 0;
    input.style.zIndex = -1;
    input.style.position = 'absolute';

    input.addEventListener(
        'blur',
        function(evt) { if (this.parentNode.onblur) this.parentNode.onblur(evt); },
        false);

    input.addEventListener(
        'focus',
        function(evt) { if (this.parentNode.onfocus) this.parentNode.onfocus(evt); },
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
    elem.focus();
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


