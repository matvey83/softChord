def getAbsoluteLeft(elem):
    left = elem.getBoundingClientRect().left
    return left + elem.ownerDocument.body.scrollLeft

def getAbsoluteTop(elem):
    top = elem.getBoundingClientRect().top
    return top + elem.ownerDocument.body.scrollTop

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

    cb = get_main_frame()._timer_callback_workaround
    global hack_timer_workaround_bug_button
    mf._hack_timer_workaround_bug_button = createButton()
    mf.addEventListener(mf._hack_timer_workaround_bug_button, "click", cb)


