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

from HTMLTable import HTMLTable
from CellFormatter import CellFormatter
from RowFormatter import RowFormatter

class Grid(HTMLTable):

    def __init__(self, rows=0, columns=0, **kwargs):
        self.numColumns = 0
        self.numRows = 0
        HTMLTable.__init__(self, **kwargs)
        if rows > 0 or columns > 0:
            self.resize(rows, columns)

    def removeRow(self, row):
        HTMLTable.removeRow(self, row)
        self.numRows -= 1

    def resize(self, rows, columns):
        self.resizeColumns(columns)
        self.resizeRows(rows)

    def resizeColumns(self, columns):
        if self.numColumns == columns:
            return

        if self.numColumns > columns:
            for i in range(0, self.numRows):
                for j in range(self.numColumns - 1, columns - 1, -1):
                    self.removeCell(i, j)
        else:
            for i in range(self.numRows):
                for j in range(self.numColumns, columns):
                    self.insertCell(i, j)
        self.numColumns = columns

    def resizeRows(self, rows):
        if self.numRows == rows:
            return

        if self.numRows < rows:
            self.addRows(self.getBodyElement(), rows - self.numRows, self.numColumns)
            self.numRows = rows
        else:
            while self.numRows > rows:
                self.removeRow(self.numRows - 1)

    def createCell(self):
        td = HTMLTable.createCell(self)
        DOM.setInnerHTML(td, "&nbsp;")
        return td

    def clearCell(self, row, column):
        td = self.cellFormatter.getElement(row, column)
        b = HTMLTable.internalClearCell(self, td)
        DOM.setInnerHTML(td, "&nbsp;")
        return b

    def prepareCell(self, row, column):
        pass

    def prepareRow(self, row):
        pass

    def getCellCount(self, row):
        return self.numColumns

    def getColumnCount(self):
        return self.numColumns

    def getRowCount(self):
        return self.numRows

    def addRows(self, table, numRows, columns):
        td = DOM.createElement("td")
        DOM.setInnerHTML(td, "&nbsp;")
        row = DOM.createElement("tr")
        for cellNum in range(columns):
            cell = td.cloneNode(True)
            row.appendChild(cell)
        for rowNum in range(numRows):
            table.appendChild(row.cloneNode(True))

Factory.registerClass('pyjamas.ui.Grid', Grid)

