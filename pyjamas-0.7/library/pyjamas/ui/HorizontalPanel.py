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

from CellPanel import CellPanel
from pyjamas.ui import HasHorizontalAlignment
from pyjamas.ui import HasVerticalAlignment

class HorizontalPanel(CellPanel):

    def __init__(self, **kwargs):

        if not kwargs.has_key('Spacing'): kwargs['Spacing'] = 0
        if not kwargs.has_key('Padding'): kwargs['Padding'] = 0

        self.horzAlign = HasHorizontalAlignment.ALIGN_LEFT
        self.vertAlign = HasVerticalAlignment.ALIGN_TOP

        CellPanel.__init__(self, **kwargs)

        self.tableRow = DOM.createTR()
        DOM.appendChild(self.getBody(), self.tableRow)

    def add(self, widget):
        self.insert(widget, self.getWidgetCount())

    def getHorizontalAlignment(self):
        return self.horzAlign

    def getVerticalAlignment(self):
        return self.vertAlign

    def insert(self, widget, beforeIndex):
        widget.removeFromParent()

        td = DOM.createTD()
        DOM.insertChild(self.tableRow, td, beforeIndex)

        CellPanel.insert(self, widget, td, beforeIndex)

        self.setCellHorizontalAlignment(widget, self.horzAlign)
        self.setCellVerticalAlignment(widget, self.vertAlign)

    def remove(self, widget):
        if isinstance(widget, int):
            widget = self.getWidget(widget)

        if widget.getParent() != self:
            return False

        td = DOM.getParent(widget.getElement())
        DOM.removeChild(self.tableRow, td)

        CellPanel.remove(self, widget)
        return True

    def setHorizontalAlignment(self, align):
        self.horzAlign = align

    def setVerticalAlignment(self, align):
        self.vertAlign = align

Factory.registerClass('pyjamas.ui.HorizontalPanel', HorizontalPanel)

