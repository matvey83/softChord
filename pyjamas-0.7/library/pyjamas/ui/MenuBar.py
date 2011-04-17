# Copyright 2006 James Tauber and contributors
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Copyright (C) 2009 Pavel Mironchyk <p.mironchyk@gmail.com>
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

from pyjamas import DeferredCommand
from Widget import Widget
from MenuItem import MenuItem
from MenuBarPopupPanel import MenuBarPopupPanel
from pyjamas.ui import Event

class MenuBar(Widget):
    def __init__(self, vertical=False, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-MenuBar"

        self.body = None
        self.items = []
        self.parentMenu = None
        self.popup = None
        self.selectedItem = None
        self.shownChildMenu = None
        self.vertical = False
        self.autoOpen = False

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

        if not vertical:
            tr = DOM.createTR()
            DOM.appendChild(self.body, tr)

        self.vertical = vertical

        outer = DOM.createDiv()
        DOM.appendChild(outer, table)
        self.setElement(outer)
        Widget.__init__(self, **kwargs)

    # also callable as:
    #   addItem(item)
    #   addItem(text, cmd)
    #   addItem(text, popup)
    #   addItem(text, asHTML, cmd)
    def addItem(self, item, asHTML=None, popup=None):
        if not hasattr(item, "setSubMenu"):
            item = MenuItem(item, asHTML, popup)

        if self.vertical:
            tr = DOM.createTR()
            DOM.appendChild(self.body, tr)
        else:
            tr = DOM.getChild(self.body, 0)

        DOM.appendChild(tr, item.getElement())

        item.setParentMenu(self)
        item.setSelectionStyle(False)
        self.items.append(item)
        return item

    def clearItems(self):
        container = self.getItemContainerElement()
        while DOM.getChildCount(container) > 0:
            DOM.removeChild(container, DOM.getChild(container, 0))
        self.items = []

    def getAutoOpen(self):
        return self.autoOpen

    def onBrowserEvent(self, event):
        Widget.onBrowserEvent(self, event)

        item = self.findItem(DOM.eventGetTarget(event))
        if item is None:
            return False

        type = DOM.eventGetType(event)
        if type == "click":
            self.doItemAction(item, True)
            return True
        elif type == "mouseover":
            self.itemOver(item)
        elif type == "mouseout":
            self.itemOver(None)

        return False

    def onPopupClosed(self, sender, autoClosed):
        if autoClosed:
            self.closeAllParents()

        self.onHide()
        self.shownChildMenu = None
        self.popup = None

    def removeItem(self, item):
        try:
            idx = self.items.index(item)
        except ValueError:
            return
        container = self.getItemContainerElement()
        DOM.removeChild(container, DOM.getChild(container, idx))
        del self.items[idx]

    def setAutoOpen(self, autoOpen):
        self.autoOpen = autoOpen

    def closeAllParents(self):
        curMenu = self
        while curMenu is not None:
            curMenu.close()

            if curMenu.parentMenu is None and curMenu.selectedItem is not None:
                curMenu.selectedItem.setSelectionStyle(False)
                curMenu.selectedItem = None

            curMenu = curMenu.parentMenu

    def doItemAction(self, item, fireCommand):
        if (self.shownChildMenu is not None) and (item.getSubMenu() == self.shownChildMenu):
            return

        if (self.shownChildMenu is not None):
            self.shownChildMenu.onHide()
            self.popup.hide()

        if item.getSubMenu() is None:
            if fireCommand:
                self.closeAllParents()

                cmd = item.getCommand()
                if cmd is not None:
                    DeferredCommand.add(cmd)
            return

        self.selectItem(item)
        self.popup = MenuBarPopupPanel(item)
        self.popup.addPopupListener(self)

        if self.vertical:
            self.popup.setPopupPosition(self.getAbsoluteLeft() + 
                                        self.getOffsetWidth() - 1,
                                        item.getAbsoluteTop())
        else:
            self.popup.setPopupPosition(item.getAbsoluteLeft(),
                   self.getAbsoluteTop() +
                   self.getOffsetHeight() - 1)

        self.shownChildMenu = item.getSubMenu()
        sub_menu = item.getSubMenu()
        sub_menu.parentMenu = self

        self.popup.show()

    def onDetach(self):
        if self.popup is not None:
            self.popup.hide()

        Widget.onDetach(self)

    def itemOver(self, item):
        if item is None:
            if (self.selectedItem is not None):
                if self.selectedItem.getSubMenu() != None:
                    if (self.shownChildMenu == self.selectedItem.getSubMenu()):
                        return
                else:
                    self.selectItem(item)
                    return

        self.selectItem(item)

        if item is not None:
            if (self.shownChildMenu is not None) or (self.parentMenu is not None) or self.autoOpen:
                self.doItemAction(item, False)

    def close(self):
        if self.parentMenu is not None:
            self.parentMenu.popup.hide()

    def findItem(self, hItem):
        for item in self.items:
            if DOM.isOrHasChild(item.getElement(), hItem):
                return item

        return None

    def getItemContainerElement(self):
        if self.vertical:
            return self.body
        else:
            return DOM.getChild(self.body, 0)

    def onHide(self):
        if self.shownChildMenu is not None:
            self.shownChildMenu.onHide()
            self.popup.hide()

    def onShow(self):
        if len(self.items) > 0:
            self.selectItem(self.items[0])

    def selectItem(self, item):
        if item == self.selectedItem:
            return

        if self.selectedItem is not None:
            self.selectedItem.setSelectionStyle(False)

        if item is not None:
            item.setSelectionStyle(True)

        self.selectedItem = item

Factory.registerClass('pyjamas.ui.MenuBar', MenuBar)

