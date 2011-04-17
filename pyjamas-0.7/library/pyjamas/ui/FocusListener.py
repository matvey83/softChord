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

def fireFocusEvent(listeners, sender, event):
    type = DOM.eventGetType(event)
    if type == "focus":
        for listener in listeners:
            listener.onFocus(sender)
    elif type == "blur":
        for listener in listeners:
            listener.onLostFocus(sender)

FOCUS_EVENTS = ["focus", "blur"]

class FocusHandler:

    def __init__(self):
        self._focusListeners = []
        self.sinkEvents( Event.FOCUSEVENTS )

    def onFocus(self, sender):
        pass

    def onLostFocus(self, sender):
        pass

    def onBrowserEvent(self, event):
        type = DOM.eventGetType(event)
        if type == "blur" or type == "focus":
            fireFocusEvent(self._focusListeners, self, event)

    def addFocusListener(self, listener):
        self._focusListeners.append(listener)

    def removeFocusListener(self, listener):
        self._focusListeners.remove(listener)

