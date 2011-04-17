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
from pyjamas.ui import Applier

class CellFormatter(Applier):

    def __init__(self, outer, **kwargs):
        self.outer = outer
        Applier.__init__(self, **kwargs)

    def addStyleName(self, row, column, styleName):
        self.outer.prepareCell(row, column)
        self.outer.setStyleName(self.getElement(row, column), styleName, True)

    def getElement(self, row, column):
        self.outer.checkCellBounds(row, column)
        return DOM.getChild(self.outer.rowFormatter.getRow(self.outer.bodyElem, row), column)

    def getStyleName(self, row, column):
        return DOM.getAttribute(self.getElement(row, column), "className")

    def isVisible(self, row, column):
        element = self.getElement(row, column)
        return self.outer.isVisible(element)

    def removeStyleName(self, row, column, styleName):
        self.outer.checkCellBounds(row, column)
        self.outer.setStyleName(self.getElement(row, column), styleName, False)

    def setAlignment(self, row, column, hAlign, vAlign):
        self.setHorizontalAlignment(row, column, hAlign)
        self.setVerticalAlignment(row, column, vAlign)

    def setHeight(self, row, column, height):
        self.outer.prepareCell(row, column)
        element = self.getCellElement(self.outer.bodyElem, row, column)
        DOM.setStyleAttribute(element, "height", height)

    def setHorizontalAlignment(self, row, column, align):
        self.outer.prepareCell(row, column)
        element = self.getCellElement(self.outer.bodyElem, row, column)
        DOM.setAttribute(element, "align", align)

    def setStyleName(self, row, column, styleName):
        self.outer.prepareCell(row, column)
        self.setAttr(row, column, "className", styleName)

    def setVerticalAlignment(self, row, column, align):
        self.outer.prepareCell(row, column)
        DOM.setStyleAttribute(self.getCellElement(self.outer.bodyElem, row, column), "verticalAlign", align)

    def setVisible(self, row, column, visible):
        element = self.ensureElement(row, column)
        self.outer.setVisible(element, visible)

    def setWidth(self, row, column, width):
        self.outer.prepareCell(row, column)
        DOM.setStyleAttribute(self.getCellElement(self.outer.bodyElem, row, column), "width", width)

    def setWordWrap(self, row, column, wrap):
        self.outer.prepareCell(row, column)
        if wrap:
            wrap_str = ""
        else:
            wrap_str = "nowrap"

        DOM.setStyleAttribute(self.getElement(row, column), "whiteSpace", wrap_str)

    def getCellElement(self, table, row, col):
        length = table.rows.length
        if row >= length:
            return None
        cols = table.rows.item(row).cells
        length = cols.length
        if col >= length:
            return None
        item = cols.item(col)
        return item

    def getRawElement(self, row, column):
        return self.getCellElement(self.outer.bodyElem, row, column)

    def ensureElement(self, row, column):
        self.outer.prepareCell(row, column)
        return DOM.getChild(self.outer.rowFormatter.ensureElement(row), column)

    def getStyleAttr(self, row, column, attr):
        elem = self.getElement(row, column)
        return DOM.getStyleAttribute(elem, attr)

    def setStyleAttr(self, row, column, attrName, value):
        elem = self.getElement(row, column)
        DOM.setStyleAttribute(elem, attrName, value)

    def getAttr(self, row, column, attr):
        elem = self.getElement(row, column)
        return DOM.getAttribute(elem, attr)

    def setAttr(self, row, column, attrName, value):
        elem = self.getElement(row, column)
        DOM.setAttribute(elem, attrName, value)



