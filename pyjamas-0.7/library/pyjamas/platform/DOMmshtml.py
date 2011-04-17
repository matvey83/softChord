
def get_listener(item):
    if item is None:
        return None
    return listeners.get(item.uniqueID)

def set_listener(item, listener):
    listeners[item.uniqueID] = listener


def _dispatchEvent(sender, event, useCap):
    if not event:
        evt = wnd().event
    else:
        evt = event
    #print "_dispatchEvent", sender, evt, evt.type, evt.returnValue

    if evt.returnValue is None:
        evt.returnValue = True
        if not previewEvent(evt):
            return

    cap = getCaptureElement()
    listener = get_listener(cap)
    if cap and listener:
        #print "_dispatchEvent capture", cap, listener
        dispatchEvent(evt, cap, listener)
        return

    curElem = sender
    while curElem and not get_listener(curElem):
        curElem = curElem.parentElement
    
    listener = get_listener(curElem)
    if listener:
        dispatchEvent(evt, curElem, listener)

def buttonClick(elem):
    newEvent = doc().createEventObject()
    elem.fireEvent('onclick', newEvent)

#def TODOinit():
#    JS("""
#    // Set up event dispatchers.
#    $wnd.__dispatchEvent = function() {
#        if ($wnd.event.returnValue == null) {
#            $wnd.event.returnValue = True
#            if (!DOM.previewEvent($wnd.event))
#                return
#        }
#
#        var listener, curElem = this
#        while (curElem and !(listener = curElem.__listener))
#            curElem = curElem.parentElement
#    
#        if (listener)
#            DOM.dispatchEvent($wnd.event, curElem, listener)
#    }
#
#    $wnd.__dispatchDblClickEvent = function() {
#        var newEvent = doc().createEventObject()
#        this.fireEvent('onclick', newEvent)
#        if (this.__eventBits & 2)
#            $wnd.__dispatchEvent.call(this)
#    }
#
#    doc().body.onclick       =
#    doc().body.onmousedown   =
#    doc().body.onmouseup     =
#    doc().body.onmousemove   =
#    doc().body.onkeydown     =
#    doc().body.onkeypress    =
#    doc().body.onkeyup       =
#    doc().body.onfocus       =
#    doc().body.onblur        =
#    doc().body.ondblclick    = $wnd.__dispatchEvent
#    """)

def init():
    
    mf = get_main_frame()
    mf._addWindowEventListener("click", browser_event_cb)
    mf._addWindowEventListener("change", browser_event_cb)
    mf._addWindowEventListener("mouseout", browser_event_cb)
    mf._addWindowEventListener("mousedown", browser_event_cb)
    mf._addWindowEventListener("mouseup", browser_event_cb)
    mf._addWindowEventListener("resize", browser_event_cb)
    mf._addWindowEventListener("keyup", browser_event_cb)
    mf._addWindowEventListener("keydown", browser_event_cb)
    mf._addWindowEventListener("keypress", browser_event_cb)

    # this is somewhat cheating, but hey.  if someone
    # ever tries to wrap body with a Widget, and attaches
    # events to it, whoops...
    body = doc().body

    mf.addEventListener(body, "click", _dispatchEvent)
    mf.addEventListener(body, "mousedown", _dispatchEvent)
    mf.addEventListener(body, "mouseup", _dispatchEvent)
    mf.addEventListener(body, "mousemove", _dispatchEvent)
    mf.addEventListener(body, "keydown", _dispatchEvent)
    mf.addEventListener(body, "keyup", _dispatchEvent)
    mf.addEventListener(body, "keypress", _dispatchEvent)
    mf.addEventListener(body, "focus", _dispatchEvent)
    mf.addEventListener(body, "blur", _dispatchEvent)
    mf.addEventListener(body, "dblclick", _dispatchEvent)

def compare(elem1, elem2):
    if not elem1 and not elem2:
        return True
    elif not elem1 or not elem2:
        return False
    return elem1.uniqueID == elem2.uniqueID

def createInputRadio(group):
    return doc().createElement("<INPUT type='RADIO' name='" + group + "'>")

def eventGetTarget(evt):
    return evt.srcElement

def eventGetToElement(evt):
    return hasattr(evt, "toElement") and evt.toElement or None

def eventPreventDefault(evt):
    evt.returnValue = False

def eventToString(evt):
    if hasattr(evt, "toString"):
        return evt.toString()
    return "[object Event]"

def getAbsoluteLeft(elem):
    scrollLeft = doc().documentElement.scrollLeft
    if scrollLeft == 0:
        scrollLeft = doc().body.scrollLeft
    
    return (elem.getBoundingClientRect().left + scrollLeft) - 2

def getAbsoluteTop(elem):
    scrollTop = doc().documentElement.scrollTop
    if scrollTop == 0:
        scrollTop = doc().body.scrollTop
    
    return (elem.getBoundingClientRect().top +  scrollTop) - 2


def getChild(elem, index):
    return elem.children.item(index)

def getChildCount(elem):
    return elem.children.length

def getChildIndex(parent, child):
    for i in range(parent.children.length):
        if child.uniqueID == parent.children.item(i).uniqueID:
            return i
    return -1

def getFirstChild(elem):
    return elem.firstChild

def getInnerText(elem):
    return elem.innerText

def getNextSibling(elem):
    return elem.nextSibling

def getParent(elem):
    return elem.parentElement

def insertChild(parent, child, index):
    if index == parent.children.length:
        parent.appendChild(child)
    else:
        parent.insertBefore(child, parent.children.item(index))

def insertListItem(select, text, value, index):
    newOption = doc().createElement("Option")
    if index==-1:
        select.add(newOption)
    else:
        select.add(newOption,index)
    newOption.text=text
    newOption.value=value

def isOrHasChild(parent, child):
    if not parent:
        return False
    while child:
        if parent.uniqueID == child.uniqueID:
            return True
        child = child.parentElement
    return False

def releaseCapture(elem):
    global sCaptureElem
    if sCaptureElem and compare(elem, sCaptureElem):
        sCaptureElem = None
    elem.releaseCapture()

def setCapture(elem):
    global sCaptureElem
    sCaptureElem = elem
    elem.setCapture()

def setInnerText(elem, text):
    if not text:
        text = ''
    elem.innerText = text

#def TODOsinkEvents(elem, bits):
#    JS("""
#    elem.__eventBits = bits
#
#    elem.onclick       = (bits & 0x00001) ? $wnd.__dispatchEvent : null
#    elem.ondblclick    = (bits & 0x00002) ? $wnd.__dispatchDblClickEvent : null
#    elem.onmousedown   = (bits & 0x00004) ? $wnd.__dispatchEvent : null
#    elem.onmouseup     = (bits & 0x00008) ? $wnd.__dispatchEvent : null
#    elem.onmouseover   = (bits & 0x00010) ? $wnd.__dispatchEvent : null
#    elem.onmouseout    = (bits & 0x00020) ? $wnd.__dispatchEvent : null
#    elem.onmousemove   = (bits & 0x00040) ? $wnd.__dispatchEvent : null
#    elem.onkeydown     = (bits & 0x00080) ? $wnd.__dispatchEvent : null
#    elem.onkeypress    = (bits & 0x00100) ? $wnd.__dispatchEvent : null
#    elem.onkeyup       = (bits & 0x00200) ? $wnd.__dispatchEvent : null
#    elem.onchange      = (bits & 0x00400) ? $wnd.__dispatchEvent : null
#    elem.onfocus       = (bits & 0x00800) ? $wnd.__dispatchEvent : null
#    elem.onblur        = (bits & 0x01000) ? $wnd.__dispatchEvent : null
#    elem.onlosecapture = (bits & 0x02000) ? $wnd.__dispatchEvent : null
#    elem.onscroll      = (bits & 0x04000) ? $wnd.__dispatchEvent : null
#    elem.onload        = (bits & 0x08000) ? $wnd.__dispatchEvent : null
#    elem.onerror       = (bits & 0x10000) ? $wnd.__dispatchEvent : null
#    elem.oncontextmenu = (bits & 0x20000) ? $wnd.__dispatchEvent : null; 
#    """)

def toString(elem):
    return elem.outerHTML

def setOptionText(select, text, index):
    option = select.options.item(index)
    option.text = text

def eventGetKeyCode(evt):
    if hasattr(evt, "which"):
        return evt.which
    if hasattr(evt, "keyCode"):
        return evt.keyCode
    return 0

def eventStopPropagation(evt):
    eventCancelBubble(evt)

