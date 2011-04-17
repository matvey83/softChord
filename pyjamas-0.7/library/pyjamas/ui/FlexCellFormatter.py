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

from CellFormatter import CellFormatter

class FlexCellFormatter(CellFormatter):
    def __init__(self, outer, **kwargs):
        CellFormatter.__init__(self, outer, **kwargs)

    def getColSpan(self, row, column):
        return DOM.getIntAttribute(self.getElement(row, column), "colSpan")

    def getRowSpan(self, row, column):
        return DOM.getIntAttribute(self.getElement(row, column), "rowSpan")

    def setColSpan(self, row, column, colSpan):
        DOM.setIntAttribute(self.ensureElement(row, column), "colSpan", colSpan)

    def setRowSpan(self, row, column, rowSpan):
        DOM.setIntAttribute(self.ensureElement(row, column), "rowSpan", rowSpan)


