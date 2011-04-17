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


from Composite import Composite
from pyjamas.ui import Event
from pyjamas.ui import Focus
from SimplePanel import SimplePanel
from pyjamas.ui import KeyboardListener

class ClickDelegatePanel(Composite):

    def __init__(self, p, child, cDelegate, kDelegate) :

        Composite.__init__(self)

        self.clickDelegate = cDelegate
        self.keyDelegate = kDelegate

        self.focusablePanel = SimplePanel(Focus.createFocusable())
        self.focusablePanel.setWidget(child)
        wrapperWidget = p.createTabTextWrapper()
        if wrapperWidget is None:
            self.initWidget(self.focusablePanel)
        else :
            wrapperWidget.setWidget(self.focusablePanel)
            self.initWidget(wrapperWidget)

        if hasattr(child, "addKeyboardListener"):
            child.addKeyboardListener(kDelegate)

        self.sinkEvents(Event.ONCLICK | Event.ONKEYDOWN)

    # receive Label's onClick and pass it through, pretending it came from us
    def onClick(self, sender=None):
        self.clickDelegate.onClick(sender)

    def getFocusablePanel(self):
        return self.focusablePanel

    def onBrowserEvent(self, event) :
        type = DOM.eventGetType(event)
        if type == "click":
            self.onClick(self)

        elif type == "keydown":
            modifiers = KeyboardListener.getKeyboardModifiers(event)
            if hasattr(self.keyDelegate, "onKeyDown"):
                self.keyDelegate.onKeyDown(self, DOM.eventGetKeyCode(event),
                                       modifiers)

# TODO: sort out how to create or grab an element for
# Factory.createWidgetOnElement to work
#Factory.registerClass('pyjamas.ui.ClickDelegatePanel', ClickDelegatePanel)

