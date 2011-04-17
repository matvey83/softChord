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
from __pyjamas__ import console
from sets import Set
import pygwt

from Widget import Widget
from pyjamas.ui import Event
from pyjamas.ui import Focus
from TreeItem import RootTreeItem, TreeItem
from pyjamas.ui import MouseListener
from pyjamas.ui import KeyboardListener
from pyjamas.ui import FocusListener

class Tree(Widget):
    def __init__(self, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-Tree"

        self.root = None
        self.childWidgets = Set()
        self.curSelection = None
        self.focusable = None
        self.focusListeners = []
        self.mouseListeners = []
        self.imageBase = pygwt.getModuleBaseURL()
        self.keyboardListeners = []
        self.listeners = []
        self.lastEventType = ""

        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createDiv()
        self.setElement(element)
        DOM.setStyleAttribute(self.getElement(), "position", "relative")
        self.focusable = Focus.createFocusable()
        # Hide focus outline in Mozilla/Webkit/Opera
        DOM.setStyleAttribute(self.focusable, "outline", "0px")
        # Hide focus outline in IE 6/7
        DOM.setElemAttribute(self.focusable, "hideFocus", "true");

        DOM.setStyleAttribute(self.focusable, "fontSize", "0")
        DOM.setStyleAttribute(self.focusable, "position", "absolute")
        DOM.setIntStyleAttribute(self.focusable, "zIndex", -1)
        DOM.appendChild(self.getElement(), self.focusable)

        self.root = RootTreeItem()
        self.root.setTree(self)

        Widget.__init__(self, **kwargs)

        self.sinkEvents(Event.ONMOUSEDOWN | Event.ONCLICK | Event.KEYEVENTS)
        #DOM.sinkEvents(self.focusable, Event.FOCUSEVENTS | Event.KEYEVENTS | DOM.getEventsSunk(self.focusable))
        DOM.sinkEvents(self.focusable, Event.FOCUSEVENTS)

    def add(self, widget):
        self.addItem(widget)

    def addFocusListener(self, listener):
        self.focusListeners.append(listener)

    def addItem(self, item):
        return self.insertItem(item)

    def insertItem(self, item, index=None):
        if isinstance(item, str):
            item = TreeItem(item)

        ret = self.root.addItem(item)
        if index is None:
            DOM.appendChild(self.getElement(), item.getElement())
        else:
            DOM.insertChild(self.getElement(), item.getElement(), index)

        return ret

    def addKeyboardListener(self, listener):
        self.keyboardListeners.append(listener)

    def addMouseListener(self, listener):
        self.mouseListeners.append(listener)

    def addTreeListener(self, listener):
        self.listeners.append(listener)

    def clear(self):
        size = self.root.getChildCount()
        for i in range(size, 0, -1):
            self.root.getChild(i-1).remove()

    def ensureSelectedItemVisible(self):
        if self.curSelection is None:
            return

        parent = self.curSelection.getParentItem()
        while parent is not None:
            parent.setState(True)
            parent = parent.getParentItem()

    def getImageBase(self):
        return self.imageBase

    def getItem(self, index):
        return self.root.getChild(index)

    def getItemCount(self):
        return self.root.getChildCount()

    def getSelectedItem(self):
        return self.curSelection

    def getTabIndex(self):
        return Focus.getTabIndex(self.focusable)

    def __iter__(self):
        return self.childWidgets.__iter__()

    def onBrowserEvent(self, event):
        type = DOM.eventGetType(event)

        if type == "click":
            e = DOM.eventGetTarget(event)
            if not self.shouldTreeDelegateFocusToElement(e):
                self.setFocus(True)
        elif type == "mousedown":
            MouseListener.fireMouseEvent(self.mouseListeners, self, event)
            self.elementClicked(self.root, DOM.eventGetTarget(event))
        elif type == "mouseup" or type == "mousemove" or type == "mouseover" or type == "mouseout":
            MouseListener.fireMouseEvent(self.mouseListeners, self, event)
        elif type == "blur" or type == "focus":
            FocusListener.fireFocusEvent(self.focusListeners, self, event)
        elif type == "keydown":
            if self.curSelection is None:
                if self.root.getChildCount() > 0:
                    self.onSelection(self.root.getChild(0), True)
                Widget.onBrowserEvent(self, event)
                return

            if self.lastEventType == "keydown":
                return

            keycode = DOM.eventGetKeyCode(event)
            if keycode == KeyboardListener.KEY_UP:
                self.moveSelectionUp(self.curSelection, True)
                DOM.eventPreventDefault(event)
            elif keycode == KeyboardListener.KEY_DOWN:
                self.moveSelectionDown(self.curSelection, True)
                DOM.eventPreventDefault(event)
            elif keycode == KeyboardListener.KEY_LEFT:
                if self.curSelection.getState():
                    self.curSelection.setState(False)
                DOM.eventPreventDefault(event)
            elif keycode == KeyboardListener.KEY_RIGHT:
                if not self.curSelection.getState():
                    self.curSelection.setState(True)
                DOM.eventPreventDefault(event)
        elif type == "keyup":
            if DOM.eventGetKeyCode(event) == KeyboardListener.KEY_TAB:
                chain = []
                self.collectElementChain(chain, self.getElement(), DOM.eventGetTarget(event))
                item = self.findItemByChain(chain, 0, self.root)
                if item != self.getSelectedItem():
                    self.setSelectedItem(item, True)
        elif type == "keypress":
            KeyboardListener.fireKeyboardEvent(self.keyboardListeners, self, event)

        Widget.onBrowserEvent(self, event)
        self.lastEventType = type

    def remove(self, widget):
        #throw new UnsupportedOperationException("Widgets should never be directly removed from a tree")
        console.error("Widgets should never be directly removed from a tree")

    def removeFocusListener(self, listener):
        self.focusListeners.remove(listener)

    def removeItem(self, item):
        self.root.removeItem(item)
        DOM.removeChild(self.getElement(), item.getElement())

    def removeItems(self):
        while self.getItemCount() > 0:
            self.removeItem(self.getItem(0))

    def removeKeyboardListener(self, listener):
        self.keyboardListeners.remove(listener)

    def removeTreeListener(self, listener):
        self.listeners.remove(listener)

    def setAccessKey(self, key):
        Focus.setAccessKey(self.focusable, key)

    def setFocus(self, focus):
        if focus:
            Focus.focus(self.focusable)
        else:
            Focus.blur(self.focusable)

    def setImageBase(self, baseUrl):
        self.imageBase = baseUrl
        self.root.updateStateRecursive()

    def setSelectedItem(self, item, fireEvents=True):
        if item is None:
            if self.curSelection is None:
                return
            self.curSelection.setSelected(False)
            self.curSelection = None
            return

        self.onSelection(item, fireEvents)

    def setTabIndex(self, index):
        Focus.setTabIndex(self.focusable, index)

    def treeItemIterator(self):
        accum = []
        self.root.addTreeItems(accum)
        return accum.__iter__()

    def collectElementChain(self, chain, hRoot, hElem):
        if (hElem is None) or DOM.compare(hElem, hRoot):
            return

        self.collectElementChain(chain, hRoot, DOM.getParent(hElem))
        chain.append(hElem)

    def elementClicked(self, root, hElem):
        chain = []
        self.collectElementChain(chain, self.getElement(), hElem)

        item = self.findItemByChain(chain, 0, root)
        if item is not None:
            if DOM.compare(item.getImageElement(), hElem):
                item.setState(not item.getState(), True)
                return True
            elif DOM.isOrHasChild(item.getElement(), hElem):
                self.onSelection(item, True)
                return True

        return False

    def findDeepestOpenChild(self, item):
        if not item.getState():
            return item
        return self.findDeepestOpenChild(item.getChild(item.getChildCount() - 1))

    def findItemByChain(self, chain, idx, root):
        if idx == len(chain):
            return root

        hCurElem = chain[idx]
        for i in range(root.getChildCount()):
            child = root.getChild(i)
            if DOM.compare(child.getElement(), hCurElem):
                retItem = self.findItemByChain(chain, idx + 1, root.getChild(i))
                if retItem is None:
                    return child
                return retItem

        return self.findItemByChain(chain, idx + 1, root)

    def moveFocus(self, selection):
        focusableWidget = selection.getFocusableWidget()
        if focusableWidget is not None:
            focusableWidget.setFocus(True)
            DOM.scrollIntoView(focusableWidget.getElement())
        else:
            selectedElem = selection.getContentElem()
            containerLeft = self.getAbsoluteLeft()
            containerTop = self.getAbsoluteTop()

            left = DOM.getAbsoluteLeft(selectedElem) - containerLeft
            top = DOM.getAbsoluteTop(selectedElem) - containerTop
            width = DOM.getIntAttribute(selectedElem, "offsetWidth")
            height = DOM.getIntAttribute(selectedElem, "offsetHeight")

            DOM.setIntStyleAttribute(self.focusable, "left", left)
            DOM.setIntStyleAttribute(self.focusable, "top", top)
            DOM.setIntStyleAttribute(self.focusable, "width", width)
            DOM.setIntStyleAttribute(self.focusable, "height", height)

            DOM.scrollIntoView(self.focusable)
            Focus.focus(self.focusable)

    def moveSelectionDown(self, sel, dig):
        if sel == self.root:
            return

        parent = sel.getParentItem()
        if parent is None:
            parent = self.root
        idx = parent.getChildIndex(sel)

        if not dig or not sel.getState():
            if idx < parent.getChildCount() - 1:
                self.onSelection(parent.getChild(idx + 1), True)
            else:
                self.moveSelectionDown(parent, False)
        elif sel.getChildCount() > 0:
            self.onSelection(sel.getChild(0), True)

    def moveSelectionUp(self, sel, climb):
        parent = sel.getParentItem()
        if parent is None:
            parent = self.root
        idx = parent.getChildIndex(sel)

        if idx > 0:
            sibling = parent.getChild(idx - 1)
            self.onSelection(self.findDeepestOpenChild(sibling), True)
        else:
            self.onSelection(parent, True)

    def onSelection(self, item, fireEvents):
        if item == self.root:
            return

        if self.curSelection is not None:
            self.curSelection.setSelected(False)

        self.curSelection = item

        if self.curSelection is not None:
            self.moveFocus(self.curSelection)
            self.curSelection.setSelected(True)
            if fireEvents and len(self.listeners):
                for listener in self.listeners:
                    listener.onTreeItemSelected(item)

    def doAttachChildren(self):
        for child in self:
            child.onAttach()
        DOM.setEventListener(self.focusable, self);

    def doDetachChildren(self):
        for child in self:
            child.onDetach()
        DOM.setEventListener(self.focusable, None);

    def onLoad(self):
        self.root.updateStateRecursive()

    def adopt(self, content):
        self.childWidgets.add(content)
        content.treeSetParent(self)

    def disown(self, item):
        self.childWidgets.remove(item)
        item.treeSetParent(None)

    def fireStateChanged(self, item):
        for listener in self.listeners:
            if hasattr(listener, "onTreeItemStateChanged"):
                listener.onTreeItemStateChanged(item)

    def getChildWidgets(self):
        return self.childWidgets

    def shouldTreeDelegateFocusToElement(self, elem):
        name = str(elem.nodeName)
        name = name.lower()
        return name == 'select' or\
               name == 'input' or\
               name == 'checkbox'

Factory.registerClass('pyjamas.ui.Tree', Tree)

