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

from Widget import Widget

class Composite(Widget):
    def __init__(self, widget=None, **kwargs):
        # this is all a bit awkward!  initialising
        # stuff that really should be done in Widget.__init__
        # allows us to call self.initWidget here and thus
        # have **kwargs applied afterwards.
        self.widget = None
        self.attached = None
        if widget:
            self.initWidget(widget)
        Widget.__init__(self, **kwargs)

    def initWidget(self, widget):
        if self.widget is not None:
            return

        widget.removeFromParent()
        self.setElement(widget.getElement())

        self.widget = widget
        widget.setParent(self)

    def isAttached(self):
        if self.widget:
            return self.widget.isAttached()
        return False

    def onAttach(self):
        #print "Composite.onAttach", self
        self.widget.onAttach()
        DOM.setEventListener(self.getElement(), self);

        self.onLoad()

    def onDetach(self):
        self.widget.onDetach()

    def setWidget(self, widget):
        self.initWidget(widget)

    def onBrowserEvent(self, event):
        Widget.onBrowserEvent(self, event) # takes care of auto-handlers
        self.widget.onBrowserEvent(event)

Factory.registerClass('pyjamas.ui.Composite', Composite)

