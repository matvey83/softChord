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

from CellPanel import CellPanel
from pyjamas.ui import HasHorizontalAlignment
from pyjamas.ui import HasVerticalAlignment

class DockPanelTmpRow:
    center = 0
    tr = None

class LayoutData:
    def __init__(self, direction):
        self.direction = direction
        self.hAlign = "left"
        self.height = ""
        self.td = None
        self.vAlign = "top"
        self.width = ""


class DockPanel(CellPanel):

    CENTER = "center"
    EAST = "east"
    NORTH = "north"
    SOUTH = "south"
    WEST = "west"

    def __init__(self, **kwargs):

        if not kwargs.has_key('Spacing'): kwargs['Spacing'] = 0
        if not kwargs.has_key('Padding'): kwargs['Padding'] = 0

        self.horzAlign = HasHorizontalAlignment.ALIGN_LEFT
        self.vertAlign = HasVerticalAlignment.ALIGN_TOP
        self.center = None
        self.dock_children = [] # TODO: can self.children be used instead?

        CellPanel.__init__(self, **kwargs)

    def add(self, widget, direction):
        if direction == self.CENTER:
            if self.center is not None:
                console.error("Only one CENTER widget may be added")
            self.center = widget

        layout = LayoutData(direction)
        widget.setLayoutData(layout)
        self.setCellHorizontalAlignment(widget, self.horzAlign)
        self.setCellVerticalAlignment(widget, self.vertAlign)

        self.dock_children.append(widget)
        self.realizeTable(widget)

    def getHorizontalAlignment(self):
        return self.horzAlign

    def getVerticalAlignment(self):
        return self.vertAlign

    def getWidgetDirection(self, widget):
        if widget.getParent() != self:
            return None
        return widget.getLayoutData().direction

    def remove(self, widget):
        if widget == self.center:
            self.center = None

        ret = CellPanel.remove(self, widget)
        if ret:
            self.dock_children.remove(widget)
            self.realizeTable(None)
        return ret

    def setCellHeight(self, widget, height):
        data = widget.getLayoutData()
        data.height = height
        if data.td:
            DOM.setStyleAttribute(data.td, "height", data.height)

    def setCellHorizontalAlignment(self, widget, align):
        data = widget.getLayoutData()
        data.hAlign = align
        if data.td:
            DOM.setAttribute(data.td, "align", data.hAlign)

    def setCellVerticalAlignment(self, widget, align):
        data = widget.getLayoutData()
        data.vAlign = align
        if data.td:
            DOM.setStyleAttribute(data.td, "verticalAlign", data.vAlign)

    def setCellWidth(self, widget, width):
        data = widget.getLayoutData()
        data.width = width
        if data.td:
            DOM.setStyleAttribute(data.td, "width", data.width)

    def setHorizontalAlignment(self, align):
        self.horzAlign = align

    def setVerticalAlignment(self, align):
        self.vertAlign = align

    def realizeTable(self, beingAdded):
        bodyElement = self.getBody()

        while DOM.getChildCount(bodyElement) > 0:
            DOM.removeChild(bodyElement, DOM.getChild(bodyElement, 0))

        rowCount = 1
        colCount = 1
        for child in self.dock_children:
            dir = child.getLayoutData().direction
            if dir == self.NORTH or dir == self.SOUTH:
                rowCount += 1
            elif dir == self.EAST or dir == self.WEST:
                colCount += 1

        rows = []
        for i in range(rowCount):
            rows.append(DockPanelTmpRow())
            rows[i].tr = DOM.createTR()
            DOM.appendChild(bodyElement, rows[i].tr)

        westCol = 0
        eastCol = colCount - 1
        northRow = 0
        southRow = rowCount - 1
        centerTd = None

        for child in self.dock_children:
            layout = child.getLayoutData()

            td = DOM.createTD()
            layout.td = td
            DOM.setAttribute(layout.td, "align", layout.hAlign)
            DOM.setStyleAttribute(layout.td, "verticalAlign", layout.vAlign)
            DOM.setAttribute(layout.td, "width", layout.width)
            DOM.setAttribute(layout.td, "height", layout.height)

            if layout.direction == self.NORTH:
                DOM.insertChild(rows[northRow].tr, td, rows[northRow].center)
                self.appendAndMaybeAdopt(td, child.getElement(), beingAdded)
                DOM.setIntAttribute(td, "colSpan", eastCol - westCol + 1)
                northRow += 1
            elif layout.direction == self.SOUTH:
                DOM.insertChild(rows[southRow].tr, td, rows[southRow].center)
                self.appendAndMaybeAdopt(td, child.getElement(), beingAdded)
                DOM.setIntAttribute(td, "colSpan", eastCol - westCol + 1)
                southRow -= 1
            elif layout.direction == self.WEST:
                row = rows[northRow]
                DOM.insertChild(row.tr, td, row.center)
                row.center += 1
                self.appendAndMaybeAdopt(td, child.getElement(), beingAdded)
                DOM.setIntAttribute(td, "rowSpan", southRow - northRow + 1)
                westCol += 1
            elif layout.direction == self.EAST:
                row = rows[northRow]
                DOM.insertChild(row.tr, td, row.center)
                self.appendAndMaybeAdopt(td, child.getElement(), beingAdded)
                DOM.setIntAttribute(td, "rowSpan", southRow - northRow + 1)
                eastCol -= 1
            elif layout.direction == self.CENTER:
                centerTd = td

        if self.center is not None:
            row = rows[northRow]
            DOM.insertChild(row.tr, centerTd, row.center)
            self.appendAndMaybeAdopt(centerTd, self.center.getElement(), beingAdded)

    def appendAndMaybeAdopt(self, parent, child, beingAdded):
        if beingAdded is not None:
            if DOM.compare(child, beingAdded.getElement()):
                CellPanel.add(self, beingAdded, parent)
                return
        DOM.appendChild(parent, child)

Factory.registerClass('pyjamas.ui.DockPanel', DockPanel)

