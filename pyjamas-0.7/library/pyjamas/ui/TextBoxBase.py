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
from pyjamas import Factory
from __pyjamas__ import console, JS
from FocusWidget import FocusWidget
from pyjamas.ui import Event

class TextBoxBase(FocusWidget):
    ALIGN_CENTER = "center"
    ALIGN_JUSTIFY = "justify"
    ALIGN_LEFT = "left"
    ALIGN_RIGHT = "right"

    def __init__(self, element, **kwargs):
        self.changeListeners = []
        self.currentEvent = None

        FocusWidget.__init__(self, element, **kwargs)
        self.sinkEvents(Event.ONCHANGE)

    def addChangeListener(self, listener):
        self.changeListeners.append(listener)

    def cancelKey(self):
        if self.currentEvent is not None:
            DOM.eventPreventDefault(self.currentEvent)

    def getCursorPos(self):
        element = self.getElement()
        try:
            return element.selectionStart
        except:
            return 0

    def getName(self):
        return DOM.getAttribute(self.getElement(), "name")

    def getSelectedText(self):
        start = self.getCursorPos()
        length = self.getSelectionLength()
        text = self.getText()
        return text[start:start + length]

    def getSelectionLength(self):
        element = self.getElement()
        try:
            return element.selectionEnd - element.selectionStart
        except:
            return 0

    # have to override Focus here for TextBoxBase
    # because FocusWidget (actually FocusMixin) assumes that
    # CreateFocusable has been used to create the element.
    # in "input box" type scenarios, it hasn't: it's created
    # by TextBox class etc.
    def setFocus(self, focused):
        if (focused):
            self.getElement().focus()
        else:
            self.getElement().blur()

    def getText(self):
        return DOM.getAttribute(self.getElement(), "value")

    def onBrowserEvent(self, event):
        FocusWidget.onBrowserEvent(self, event)

        type = DOM.eventGetType(event)
        if type == "change":
            for listener in self.changeListeners:
                if hasattr(listener, 'onChange'): listener.onChange(self)
                else: listener(self)

    def removeChangeListener(self, listener):
        self.changeListeners.remove(listener)

    def selectAll(self):
        length = len(self.getText())
        if length > 0:
            self.setSelectionRange(0, length)

    def setCursorPos(self, pos):
        self.setSelectionRange(pos, 0)

    def setKey(self, key):
        if self.currentEvent is not None:
            DOM.eventSetKeyCode(self.currentEvent, key)

    def setName(self, name):
        DOM.setAttribute(self.getElement(), "name", name)

    def setSelectionRange(self, pos, length):
        if length < 0:
            # throw new IndexOutOfBoundsException("Length must be a positive integer. Length: " + length);
            console.error("Length must be a positive integer. Length: " + length)

        if (pos < 0) or (length + pos > len(self.getText())):
            #throw new IndexOutOfBoundsException("From Index: " + pos + "  To Index: " + (pos + length) + "  Text Length: " + getText().length());
            console.error("From Index: " + pos + "  To Index: " + (pos + length) + "  Text Length: " + len(self.getText()))

        element = self.getElement()
        element.setSelectionRange(pos, pos + length)

    def setText(self, text):
        DOM.setAttribute(self.getElement(), "value", str(text))

    def setTextAlignment(self, align):
        DOM.setStyleAttribute(self.getElement(), "textAlign", align)

# TODO: work out if TextBoxBase is appropriate to create in Factory.
# Factory.registerClass('pyjamas.ui.TextBoxBase', TextBoxBase)

