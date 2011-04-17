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

from Composite import Composite
from DeckPanel import DeckPanel
from VerticalPanel import VerticalPanel
from TabBar import TabBar

class TabPanel(Composite):
    def __init__(self, tabBar=None, **kwargs):
        self.tab_children = [] # TODO: can self.children be used instead?
        self.deck = DeckPanel(StyleName="gwt-TabPanelBottom")
        if tabBar is None:
            self.tabBar = TabBar()
        else:
            self.tabBar = tabBar
        self.tabListeners = []

        # this is awkward: VerticalPanel is the composite,
        # so we get the element here, and pass it in to VerticalPanel.
        element = None
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')

        panel = VerticalPanel(Element=element)
        panel.add(self.tabBar)
        panel.add(self.deck)

        panel.setCellHeight(self.deck, "100%")
        self.tabBar.setWidth("100%")
        self.tabBar.addTabListener(self)

        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-TabPanel"

        Composite.__init__(self, panel, **kwargs)

    def add(self, widget, tabText=None, asHTML=False):
        """ tabText=None now means insert a spacer, pushed out at 100%
            width so that any subsequent tabs added will be pushed to
            the right hand side
        """
        self.insert(widget, tabText, asHTML, self.getWidgetCount())

    def addTabListener(self, listener):
        self.tabListeners.append(listener)

    def clear(self):
        while self.getWidgetCount() > 0:
            self.remove(self.getWidget(0))

    def getDeckPanel(self):
        return self.deck

    def getTabBar(self):
        return self.tabBar

    def getWidget(self, index):
        return self.tab_children[index]

    def getWidgetCount(self):
        return len(self.tab_children)

    def getWidgetIndex(self, child):
        return self.tab_children.index(child)

    def insert(self, widget, tabText, asHTML=False, beforeIndex=None):
        if beforeIndex is None:
            beforeIndex = asHTML
            asHTML = False

        self.tab_children.insert(beforeIndex, widget)
        self.tabBar.insertTab(tabText, asHTML, beforeIndex)
        self.deck.insert(widget, beforeIndex)

    def __iter__(self):
        return self.tab_children.__iter__()

    def onBeforeTabSelected(self, sender, tabIndex):
        for listener in self.tabListeners:
            if not listener.onBeforeTabSelected(sender, tabIndex):
                return False
        return True

    def onTabSelected(self, sender, tabIndex):
        self.deck.showWidget(tabIndex)
        for listener in self.tabListeners:
            listener.onTabSelected(sender, tabIndex)

    def remove(self, widget):
        if isinstance(widget, int):
            widget = self.getWidget(widget)

        index = self.getWidgetIndex(widget)
        if index == -1:
            return False

        self.tab_children.remove(widget)
        self.tabBar.removeTab(index)
        self.deck.remove(widget)
        return True

    def removeTabListener(self, listener):
        self.tabListeners.remove(listener)

    def selectTab(self, index):
        self.tabBar.selectTab(index)

Factory.registerClass('pyjamas.ui.TabPanel', TabPanel)

