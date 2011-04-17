def init():
    JS("""
    // Set up event dispatchers.
    $wnd.__dispatchEvent = function() {
        if ($wnd.event.returnValue == null) {
            $wnd.event.returnValue = true;
            if (!DOM.previewEvent($wnd.event))
                return;
        }

        var listener, curElem = this;
        while (curElem && !(listener = curElem.__listener))
            curElem = curElem.parentElement;
    
        if (listener)
            DOM.dispatchEvent($wnd.event, curElem, listener);
    };

    $wnd.__dispatchDblClickEvent = function() {
        var newEvent = $doc.createEventObject();
        this.fireEvent('onclick', newEvent);
        if (this.__eventBits & 2)
            $wnd.__dispatchEvent.call(this);
    };

    $doc.body.onclick       =
    $doc.body.onmousedown   =
    $doc.body.onmouseup     =
    $doc.body.onmousemove   =
    $doc.body.onkeydown     =
    $doc.body.onkeypress    =
    $doc.body.onkeyup       =
    $doc.body.onfocus       =
    $doc.body.onblur        =
    $doc.body.ondblclick    = $wnd.__dispatchEvent;
    """)

def compare(elem1, elem2):
    JS("""
    if (!elem1 && !elem2)
        return true;
    else if (!elem1 || !elem2)
        return false;
    return (elem1.uniqueID == elem2.uniqueID);
    """)

def createInputRadio(group):
    JS("""
    return $doc.createElement("<INPUT type='RADIO' name='" + group + "'>");
    """)

def eventGetCurrentTarget(event):
    return event.currentEventTarget

def eventGetTarget(evt):
    JS("""
    var elem = evt.srcElement;
    return elem ? elem : null;
    """)

def eventGetToElement(evt):
    JS("""
    return evt.toElement ? evt.toElement : null;
    """)

def eventPreventDefault(evt):
    JS("""
    evt.returnValue = false;
    """)

def eventToString(evt):
    JS("""
    if (evt.toString) return evt.toString();
    return "[object Event]";
    """)

def getBodyOffsetTop():
    JS("""
    return $doc.body.parentElement.clientTop;
    """)

def getBodyOffsetLeft():
    JS("""
    return $doc.body.parentElement.clientLeft;
    """)

def getAbsoluteLeft(elem):
    JS("""
    // getBoundingClientRect() throws a JS exception if the elem is not attached
    // to the document, so we wrap it in a try/catch block
    var zoomMultiple = $doc.body.parentElement.offsetWidth / 
                       $doc.body.offsetWidth;
    try {
        return Math.floor((elem.getBoundingClientRect().left / zoomMultiple) +
                            $doc.body.parentElement.scrollLeft );
    } catch (e) {
        return 0;
    }
    """)

def getAbsoluteTop(elem):
    JS("""
    // getBoundingClientRect() throws a JS exception if the elem is not attached
    // to the document, so we wrap it in a try/catch block
    var zoomMultiple = $doc.body.parentElement.offsetWidth / 
                       $doc.body.offsetWidth;
    try {
        var scrollTop = $doc.parent ? $doc.parent.body.scrollTop : 0;
        scrollTop += $doc.body.scrollTop;
        return Math.floor((elem.getBoundingClientRect().top / zoomMultiple) +
                            scrollTop);
    } catch (e) {
        return 0;
    }
    """)


def getChild(elem, index):
    JS("""
    var child = elem.children[index];
    return child ? child : null;
    """)

def getChildCount(elem):
    JS("""
    return elem.children.length;
    """)

def getChildIndex(parent, child):
    JS("""
    var count = parent.children.length;
    for (var i = 0; i < count; ++i) {
        if (child.uniqueID == parent.children[i].uniqueID)
            return i;
    }
    return -1;
    """)

def getFirstChild(elem):
    JS("""
    var child = elem.firstChild;
    return child ? child : null;
    """)

def getInnerText(elem):
    JS("""
    var ret = elem.innerText;
    return (ret == null) ? null : ret;
    """)

def getNextSibling(elem):
    JS("""
    var sib = elem.nextSibling;
    return sib ? sib : null;
    """)

def getParent(elem):
    JS("""
    var parent = elem.parentElement;
    return parent ? parent : null;
    """)

def insertChild(parent, child, index):
    JS("""
    if (index == parent.children.length)
        parent.appendChild(child);
    else
        parent.insertBefore(child, parent.children[index]);
    """)

def insertListItem(select, text, value, index):
    JS("""
    var newOption = document.createElement("Option");
    if(index==-1) {
        select.add(newOption);
    } else {
        select.add(newOption,index);
    }
    newOption.text=text;
    newOption.value=value;
    """)

def isOrHasChild(parent, child):
    JS("""
    while (child) {
        if (parent.uniqueID == child.uniqueID)
            return true;
        child = child.parentElement;
    }
    return false;
    """)

def releaseCapture(elem):
    JS("""
    elem.releaseCapture();
    """)

def setCapture(elem):
    JS("""
    elem.setCapture();
    """)

def setInnerText(elem, text):
    JS("""
    if (!text)
        text = '';
    elem.innerText = text;
    """)

def sinkEvents(elem, bits):
    JS("""
    elem.__eventBits = bits;

    elem.onclick       = (bits & 0x00001) ? $wnd.__dispatchEvent : null;
    elem.ondblclick    = (bits & 0x00002) ? $wnd.__dispatchDblClickEvent : null;
    elem.onmousedown   = (bits & 0x00004) ? $wnd.__dispatchEvent : null;
    elem.onmouseup     = (bits & 0x00008) ? $wnd.__dispatchEvent : null;
    elem.onmouseover   = (bits & 0x00010) ? $wnd.__dispatchEvent : null;
    elem.onmouseout    = (bits & 0x00020) ? $wnd.__dispatchEvent : null;
    elem.onmousemove   = (bits & 0x00040) ? $wnd.__dispatchEvent : null;
    elem.onkeydown     = (bits & 0x00080) ? $wnd.__dispatchEvent : null;
    elem.onkeypress    = (bits & 0x00100) ? $wnd.__dispatchEvent : null;
    elem.onkeyup       = (bits & 0x00200) ? $wnd.__dispatchEvent : null;
    elem.onchange      = (bits & 0x00400) ? $wnd.__dispatchEvent : null;
    elem.onfocus       = (bits & 0x00800) ? $wnd.__dispatchEvent : null;
    elem.onblur        = (bits & 0x01000) ? $wnd.__dispatchEvent : null;
    elem.onlosecapture = (bits & 0x02000) ? $wnd.__dispatchEvent : null;
    elem.onscroll      = (bits & 0x04000) ? $wnd.__dispatchEvent : null;
    elem.onload        = (bits & 0x08000) ? $wnd.__dispatchEvent : null;
    elem.onerror       = (bits & 0x10000) ? $wnd.__dispatchEvent : null;
    elem.oncontextmenu = (bits & 0x20000) ? $wnd.__dispatchEvent : null; 
    """)

def toString(elem):
    JS("""
    return elem.outerHTML;
    """)

def eventStopPropagation(evt):
    eventCancelBubble(evt)

