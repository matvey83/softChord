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
from __pyjamas__ import console
from pyjamas import Factory
from pyjamas import DOM

from Widget import Widget

class Panel(Widget):
    def __init__(self, **kwargs):
        self.children = []
        Widget.__init__(self, **kwargs)

    def add(self):
        console.error("This panel does not support no-arg add()")

    def clear(self):
        # use this method, due to list changing as it's being iterated.
        children = []
        for child in self.children:
            children.append(child)

        for child in children:
            self.remove(child)

    def disown(self, widget):
        if widget.getParent() != self:
            console.error("widget %o is not a child of this panel %o", widget, self)
        else:
            element = widget.getElement()
            widget.setParent(None)
            parentElement = DOM.getParent(element)
            if parentElement:
                DOM.removeChild(parentElement, element)

    def adopt(self, widget, container):
        if container:
            widget.removeFromParent()
            DOM.appendChild(container, widget.getElement())
        widget.setParent(self)

    def remove(self, widget):
        pass

    def doAttachChildren(self):
        for child in self:
            child.onAttach()

    def doDetachChildren(self):
        for child in self:
            child.onDetach()

    def __iter__(self):
        return self.children.__iter__()

Factory.registerClass('pyjamas.ui.Panel', Panel)

