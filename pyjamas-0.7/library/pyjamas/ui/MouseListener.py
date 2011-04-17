# Copyright 2006 James Tauber and contributors
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from pyjamas import DOM
from pyjamas.ui import Event

def fireMouseEvent(listeners, sender, event):
    x = DOM.eventGetClientX(event) - DOM.getAbsoluteLeft(sender.getElement())
    y = DOM.eventGetClientY(event) - DOM.getAbsoluteTop(sender.getElement())

    type = DOM.eventGetType(event)
    if type == "mousedown":
        for listener in listeners:
            listener.onMouseDown(sender, x, y)
    elif type == "mouseup":
        for listener in listeners:
            listener.onMouseUp(sender, x, y)
    elif type == "mousemove":
        for listener in listeners:
            listener.onMouseMove(sender, x, y)
    elif type == "mouseover":
        from_element = DOM.eventGetFromElement(event)
        if not DOM.isOrHasChild(sender.getElement(), from_element):
            for listener in listeners:
                listener.onMouseEnter(sender)
    elif type == "mouseout":
        to_element = DOM.eventGetToElement(event)
        if not DOM.isOrHasChild(sender.getElement(), to_element):
            for listener in listeners:
                listener.onMouseLeave(sender)

MOUSE_EVENTS = [ "mousedown", "mouseup", "mousemove", "mouseover", "mouseout"]

class MouseHandler(object):

    def __init__(self, preventDefault=False):

        self._mouseListeners = []
        self._mousePreventDefault = preventDefault
        self.sinkEvents( Event.MOUSEEVENTS )

    def onBrowserEvent(self, event):
        type = DOM.eventGetType(event)
        if type in MOUSE_EVENTS:
            if self._mousePreventDefault:
                DOM.eventPreventDefault(event)
            fireMouseEvent(self._mouseListeners, self, event)

    def addMouseListener(self, listener):
        self._mouseListeners.append(listener)

    def removeMouseListener(self, listener):
        self._mouseListeners.remove(listener)

    def onMouseMove(self, sender, x, y):
        pass
        
    def onMouseDown(self, sender, x, y):
        pass

    def onMouseUp(self, sender, x, y):
        pass

    def onMouseEnter(self, sender):
        pass

    def onMouseLeave(self, sender):
        pass

