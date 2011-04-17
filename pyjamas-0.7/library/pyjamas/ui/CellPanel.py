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

class CellPanel(ComplexPanel):

    def __init__(self, **kwargs):
        element = None
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        if element is None:
            element = DOM.createTable()
        self.table = element
        self.setElement(self.table)
        self.body = DOM.createTBody()
        self.spacing = None
        self.padding = None
        DOM.appendChild(self.table, self.body)

        ComplexPanel.__init__(self, **kwargs)

    def getTable(self):
        return self.table

    def getBody(self):
        return self.body

    def getSpacing(self):
        return self.spacing

    def getPadding(self):
        return self.padding

    def getWidgetTd(self, widget):
        if widget.getParent() != self:
            return None
        return DOM.getParent(widget.getElement())

    def setBorderWidth(self, width):
        DOM.setAttribute(self.table, "border", "%d" % width)

    def setCellHeight(self, widget, height):
        td = DOM.getParent(widget.getElement())
        DOM.setAttribute(td, "height", height)

    def setCellHorizontalAlignment(self, widget, align):
        td = self.getWidgetTd(widget)
        if td is not None:
            DOM.setAttribute(td, "align", align)

    def setCellVerticalAlignment(self, widget, align):
        td = self.getWidgetTd(widget)
        if td is not None:
            DOM.setStyleAttribute(td, "verticalAlign", align)

    def setCellWidth(self, widget, width):
        td = DOM.getParent(widget.getElement())
        DOM.setAttribute(td, "width", width)

    def setSpacing(self, spacing):
        self.spacing = spacing
        DOM.setAttribute(self.table, "cellSpacing", str(spacing))

    def setPadding(self, padding):
        self.padding = padding
        DOM.setAttribute(self.table, "cellPadding", str(padding))

Factory.registerClass('pyjamas.ui.CellPanel', CellPanel)

