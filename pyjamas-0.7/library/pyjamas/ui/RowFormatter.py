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
from pyjamas.ui import Applier

class RowFormatter(Applier):

    def __init__(self, outer, **kwargs):
        self.outer = outer
        Applier.__init__(self, **kwargs)

    def addStyleName(self, row, styleName):
        self.outer.setStyleName(self.ensureElement(row), styleName, True)

    def getElement(self, row):
        self.outer.checkRowBounds(row)
        return self.getRow(self.outer.bodyElem, row)

    def getStyleName(self, row):
        return DOM.getAttribute(self.getElement(row), "className")

    def isVisible(self, row):
        element = self.getElement(row)
        return self.outer.isVisible(element)

    def removeStyleName(self, row, styleName):
        self.outer.setStyleName(self.getElement(row), styleName, False)

    def setStyleName(self, row, styleName):
        elem = self.ensureElement(row)
        DOM.setAttribute(elem, "className", styleName)

    def setVerticalAlign(self, row, align):
        DOM.setStyleAttribute(self.ensureElement(row), "verticalAlign", align)

    def setVisible(self, row, visible):
        element = self.ensureElement(row)
        self.outer.setVisible(element, visible)

    def ensureElement(self, row):
        self.outer.prepareRow(row)
        return self.getRow(self.outer.bodyElem, row)

    def getRow(self, element, row):
        return element.rows.item(row)

    def setStyleAttr(self, row, attrName, value):
        element = self.ensureElement(row)
        DOM.setStyleAttribute(element, attrName, value)

    def setAttr(self, row, attrName, value):
        element = self.ensureElement(row)
        DOM.setAttribute(element, attrName, value)


