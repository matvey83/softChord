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

from FocusWidget import FocusWidget
from pyjamas.ui import Event
from __pyjamas__ import console

class ListBox(FocusWidget):
    def __init__(self, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-ListBox"
        self.changeListeners = []
        self.INSERT_AT_END = -1
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createSelect()
        FocusWidget.__init__(self, element, **kwargs)
        self.sinkEvents(Event.ONCHANGE)

    def addChangeListener(self, listener):
        self.changeListeners.append(listener)

    def addItem(self, item, value = None):
        self.insertItem(item, value, self.INSERT_AT_END)

    def clear(self):
        h = self.getElement()
        while DOM.getChildCount(h) > 0:
            DOM.removeChild(h, DOM.getChild(h, 0))

    def getItemCount(self):
        return DOM.getChildCount(self.getElement())

    def getItemText(self, index):
        child = DOM.getChild(self.getElement(), index)
        return DOM.getInnerText(child)

    def getName(self):
        return DOM.getAttribute(self.getElement(), "name")

    def getSelectedIndex(self):
        """ returns the selected item's index on a single-select
            listbox.  returns -1 if no item is selected.
            for multi-select, use repeated calls to isItemSelected.
        """
        return DOM.getIntAttribute(self.getElement(), "selectedIndex")

    def getValue(self, index):
        self.checkIndex(index)

        option = DOM.getChild(self.getElement(), index)
        return DOM.getAttribute(option, "value")

    def getVisibleItemCount(self):
        return DOM.getIntAttribute(self.getElement(), "size")

    # also callable as insertItem(item, index)
    def insertItem(self, item, value, index=None):
        if index is None:
            index = value
            value = None
        DOM.insertListItem(self.getElement(), item, value, index)

    def isItemSelected(self, index):
        self.checkIndex(index)
        option = DOM.getChild(self.getElement(), index)
        return DOM.getBooleanAttribute(option, "selected")

    def isMultipleSelect(self):
        return DOM.getBooleanAttribute(self.getElement(), "multiple")

    def onBrowserEvent(self, event):
        if DOM.eventGetType(event) == "change":
            for listener in self.changeListeners:
                if hasattr(listener, 'onChange'):
                    listener.onChange(self)
                else:
                    listener(self)
        else:
            FocusWidget.onBrowserEvent(self, event)

    def removeChangeListener(self, listener):
        self.changeListeners.remove(listener)

    def removeItem(self, idx):
        child = DOM.getChild(self.getElement(), idx)
        DOM.removeChild(self.getElement(), child)

    def setItemSelected(self, index, selected):
        self.checkIndex(index)
        option = DOM.getChild(self.getElement(), index)
        DOM.setIntAttribute(option, "selected", selected and 1 or 0)

    def setMultipleSelect(self, multiple):
        DOM.setBooleanAttribute(self.getElement(), "multiple", multiple)

    def setName(self, name):
        DOM.setAttribute(self.getElement(), "name", name)

    def setSelectedIndex(self, index):
        DOM.setIntAttribute(self.getElement(), "selectedIndex", index)

    def selectValue(self, value):
        """ selects the ListBox according to a value.
            to select by item, see selectItem.
            # http://code.google.com/p/pyjamas/issues/detail?id=63
        """
        for n in range(self.getItemCount()):
            if self.getValue(n) == value:
                self.setSelectedIndex(n)
                return n
        return None

    def selectItem(self, item):
        """ selects the ListBox according to an item's text
            to select by value, see selectValue.
            # http://code.google.com/p/pyjamas/issues/detail?id=63
        """
        for n in range(self.getItemCount()):
            if self.getItemText(n) == item:
                self.setSelectedIndex(n)
                return n
        return None

    def setItemText(self, index, text):
        self.checkIndex(index)
        if text is None:
            console.error("Cannot set an option to have null text")
            return
        DOM.setOptionText(self.getElement(), text, index)

    def setValue(self, index, value):
        self.checkIndex(index)

        option = DOM.getChild(self.getElement(), index)
        DOM.setAttribute(option, "value", value)

    def setVisibleItemCount(self, visibleItems):
        DOM.setIntAttribute(self.getElement(), "size", visibleItems)

    def checkIndex(self, index):
        elem = self.getElement()
        if (index < 0) or (index >= DOM.getChildCount(elem)):
            #throw new IndexOutOfBoundsException();
            pass

    def getSelectedItemText(self, ignore_first_value = False):
        selected = []
        if ignore_first_value:
            start_idx = 1
        else:
            start_idx = 0
        for i in range(start_idx,self.getItemCount()):
            if self.isItemSelected(i):
                selected.append(self.getItemText(i))
        return selected

    def getSelectedValues(self, ignore_first_value = False):
        selected = []
        if ignore_first_value:
            start_idx = 1
        else:
            start_idx = 0
        for i in range(start_idx,self.getItemCount()):
            if self.isItemSelected(i):
                selected.append(self.getValue(i))
        return selected

    def setItemTextSelection(self, values):
        if not values:
            values = []
            self.setSelectedIndex(0)
        for i in range(0,self.getItemCount()):
            if self.getItemText(i) in values:
                self.setItemSelected(i, "selected")
            else:
                self.setItemSelected(i, "")

    def setValueSelection(self, values):
        if not values:
            values = []
            self.setSelectedIndex(0)
        for i in range(0,self.getItemCount()):
            if self.getValue(i) in values:
                self.setItemSelected(i, "selected")
            else:
                self.setItemSelected(i, "")

Factory.registerClass('pyjamas.ui.ListBox', ListBox)

