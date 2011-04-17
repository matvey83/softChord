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

from ComplexPanel import ComplexPanel
from pyjamas.ui import Event

class StackPanel(ComplexPanel):

    def __init__(self, **kwargs):
        self.body = None
        self.visibleStack = -1
        self.indices = {}

        if kwargs.has_key('Element'):
            table = kwargs.pop('Element')
            fc = DOM.getFirstChild(table)
            if fc:
                self.body = fc
            else:
                self.body = DOM.createTBody()
                DOM.appendChild(table, self.body)
        else:
            table = DOM.createTable()
            self.body = DOM.createTBody()
            DOM.appendChild(table, self.body)

        self.setElement(table)

        if not kwargs.has_key('Spacing'): kwargs['Spacing'] = 0
        if not kwargs.has_key('Padding'): kwargs['Padding'] = 0
        if not kwargs.has_key('StyleName'): kwargs['StyleName'] = "gwt-StackPanel"

        DOM.sinkEvents(table, Event.ONCLICK)

        ComplexPanel.__init__(self, **kwargs)

    def add(self, widget, stackText="", asHTML=False):
        widget.removeFromParent()
        index = self.getWidgetCount()

        tr = DOM.createTR()
        td = DOM.createTD()
        DOM.appendChild(self.body, tr)
        DOM.appendChild(tr, td)
        self.setStyleName(td, "gwt-StackPanelItem", True)
        self._setIndex(td, index)
        DOM.setAttribute(td, "height", "1px")

        tr = DOM.createTR()
        td = DOM.createTD()
        DOM.appendChild(self.body, tr)
        DOM.appendChild(tr, td)
        DOM.setAttribute(td, "height", "100%")
        DOM.setAttribute(td, "vAlign", "top")

        ComplexPanel.add(self, widget, td)

        self.setStackVisible(index, False)
        if self.visibleStack == -1:
            self.showStack(0)

        if stackText != "":
            self.setStackText(self.getWidgetCount() - 1, stackText, asHTML)

    def onBrowserEvent(self, event):
        if DOM.eventGetType(event) == "click":
            index = self.getDividerIndex(DOM.eventGetTarget(event))
            if index != -1:
                self.showStack(index)

    # also callable as remove(child) and remove(index)
    def remove(self, child, index=None):
        if index is None:
            if isinstance(child, int):
                index = child
                child = self.getWidget(child)
            else:
                index = self.getWidgetIndex(child)

        if child.getParent() != self:
            return False

        if self.visibleStack == index:
            self.visibleStack = -1
        elif self.visibleStack > index:
            self.visibleStack -= 1

        rowIndex = 2 * index
        tr = DOM.getChild(self.body, rowIndex)
        DOM.removeChild(self.body, tr)
        tr = DOM.getChild(self.body, rowIndex)
        DOM.removeChild(self.body, tr)
        ComplexPanel.remove(self, child)
        rows = self.getWidgetCount() * 2

        #for (int i = rowIndex; i < rows; i = i + 2) {
        for i in range(rowIndex, rows, 2):
            childTR = DOM.getChild(self.body, i)
            td = DOM.getFirstChild(childTR)
            curIndex = self._getIndex(td)
            self._setIndex(td, index)
            index += 1

        return True

    def _setIndex(self, td, index):
        self.indices[td] = index

    def _getIndex(self, td):
        return self.indices.get(td)

    def setStackText(self, index, text, asHTML=False):
        if index >= self.getWidgetCount():
            return

        td = DOM.getChild(DOM.getChild(self.body, index * 2), 0)
        if asHTML:
            DOM.setInnerHTML(td, text)
        else:
            DOM.setInnerText(td, text)

    def showStack(self, index):
        if (index >= self.getWidgetCount()) or (index == self.visibleStack):
            return

        if self.visibleStack >= 0:
            self.setStackVisible(self.visibleStack, False)

        self.visibleStack = index
        self.setStackVisible(self.visibleStack, True)

    def getDividerIndex(self, elem):
        while (elem is not None) and not DOM.compare(elem, self.getElement()):
            expando = self._getIndex(elem)
            if expando is not None:
                return int(expando)

            elem = DOM.getParent(elem)

        return -1

    def setStackVisible(self, index, visible):
        tr = DOM.getChild(self.body, (index * 2))
        if tr is None:
            return

        td = DOM.getFirstChild(tr)
        self.setStyleName(td, "gwt-StackPanelItem-selected", visible)

        tr = DOM.getChild(self.body, (index * 2) + 1)
        self.setVisible(tr, visible)
        self.getWidget(index).setVisible(visible)

    def getSelectedIndex(self):
        return self.visibleStack

Factory.registerClass('pyjamas.ui.StackPanel', StackPanel)

