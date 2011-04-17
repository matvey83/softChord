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


KEY_ALT = 18
KEY_BACKSPACE = 8
KEY_CTRL = 17
KEY_DELETE = 46
KEY_DOWN = 40
KEY_END = 35
KEY_ENTER = 13
KEY_ESCAPE = 27
KEY_HOME = 36
KEY_LEFT = 37
KEY_PAGEDOWN = 34
KEY_PAGEUP = 33
KEY_RIGHT = 39
KEY_SHIFT = 16
KEY_TAB = 9
KEY_UP = 38

MODIFIER_ALT = 4
MODIFIER_CTRL = 2
MODIFIER_SHIFT = 1

def getKeyboardModifiers(event):
    shift = 0
    ctrl = 0
    alt = 0

    if DOM.eventGetShiftKey(event):
        shift = MODIFIER_SHIFT

    if DOM.eventGetCtrlKey(event):
        ctrl = MODIFIER_CTRL

    if DOM.eventGetAltKey(event):
        alt = MODIFIER_ALT

    return shift | ctrl | alt


def fireKeyboardEvent(listeners, sender, event):
    modifiers = getKeyboardModifiers(event)
    keycode = DOM.eventGetKeyCode(event)

    type = DOM.eventGetType(event)
    if type == "keydown":
        for listener in listeners:
            listener.onKeyDown(sender, keycode, modifiers)
    elif type == "keyup":
        for listener in listeners:
            listener.onKeyUp(sender, keycode, modifiers)
    elif type == "keypress":
        for listener in listeners:
            listener.onKeyPress(sender, keycode, modifiers)

KEYBOARD_EVENTS = ["keydown", "keyup", "keypress"]


class KeyboardHandler:

    def __init__(self):

        self._keyboardListeners = []
        self.sinkEvents( Event.KEYEVENTS )

    def onBrowserEvent(self, event):
        type = DOM.eventGetType(event)
        if type in [ "keydown", "keyup", "keypress" ]:
            fireKeyboardEvent(self._keyboardListeners, self, event)

    def addKeyboardListener(self, listener):
        self._keyboardListeners.append(listener)

    def removeKeyboardListener(self, listener):
        self._keyboardListeners.remove(listener)

    def onKeyDown(self, sender, keycode, modifiers):
        pass

    def onKeyUp(self, sender, keycode, modifiers):
        pass

    def onKeyPress(self, sender, keycode, modifiers):
        pass
