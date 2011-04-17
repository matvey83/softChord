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

from Panel import Panel

class ComplexPanel(Panel):
    """
        Superclass for widgets with multiple children.
    """
    def add(self, widget, container):
        self.insert(widget, container, len(self.children))

    def getWidgetCount(self):
        return len(self.children)

    def getWidget(self, index):
        return self.children[index]

    def getWidgetIndex(self, child):
        return self.children.index(child)

    def getChildren(self):
        return self.children

    def insert(self, widget, container, beforeIndex):
        if widget.getParent() == self:
            return

        self.adopt(widget, container)
        self.children.insert(beforeIndex, widget)

        # this code introduces an obscure IE6 bug that corrupts its DOM tree!
        #widget.removeFromParent()
        #self.children.insert(beforeIndex, widget)
        #DOM.insertChild(container, widget.getElement(), beforeIndex)
        #self.adopt(widget, container)

    def remove(self, widget):
        if widget not in self.children:
            return False

        self.disown(widget)
        #elem = self.getElement()
        #DOM.removeChild(DOM.getParent(elem), elem)
        self.children.remove(widget)
        return True

Factory.registerClass('pyjamas.ui.ComplexPanel', ComplexPanel)

