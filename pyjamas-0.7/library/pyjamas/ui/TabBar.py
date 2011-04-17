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
from Composite import Composite
from pyjamas.ui import Event
from HTML import HTML
from Label import Label
from HorizontalPanel import HorizontalPanel
from ClickDelegatePanel import ClickDelegatePanel
from pyjamas.ui import HasAlignment

class TabBar(Composite):

    STYLENAME_DEFAULT = "gwt-TabBarItem"

    def __init__(self, **kwargs):

        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-TabBar"

        # this is awkward: HorizontalPanel is the composite,
        # so we either the element here, and pass it in to HorizontalPanel.
        element = None
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')

        self.panel = HorizontalPanel(Element=element)
        self.selectedTab = None
        self.tabListeners = []

        self.panel.setVerticalAlignment(HasAlignment.ALIGN_BOTTOM)

        first = HTML("&nbsp;", True)
        rest = HTML("&nbsp;", True)
        first.setStyleName("gwt-TabBarFirst")
        rest.setStyleName("gwt-TabBarRest")
        first.setHeight("100%")
        rest.setHeight("100%")

        self.panel.add(first)
        self.panel.add(rest)
        first.setHeight("100%")
        self.panel.setCellHeight(first, "100%")
        self.panel.setCellWidth(rest, "100%")

        Composite.__init__(self, self.panel, **kwargs)
        self.sinkEvents(Event.ONCLICK)

    def addTab(self, text, asHTML=False):
        self.insertTab(text, asHTML, self.getTabCount())

    def addTabListener(self, listener):
        self.tabListeners.append(listener)

    def getSelectedTab(self):
        if self.selectedTab is None:
            return -1
        return self.panel.getWidgetIndex(self.selectedTab) - 1

    def getTabCount(self):
        return self.panel.getWidgetCount() - 2

    def getTabHTML(self, index):
        if index >= self.getTabCount():
            return None
        delPanel = self.panel.getWidget(index + 1)
        focusablePanel = delPanel.getFocusablePanel()
        widget = focusablePanel.getWidget()
        if hasattr(widget, "getHTML"):
            return widget.getHTML()
        elif hasattr(widget, "getText"): # assume it's a Label if it has getText
            return widget.getText()
        else:
            fpe = DOM.getParent(self.focusablePanel.getElement())
            return DOM.getInnerHTML(fpe)

    def createTabTextWrapper(self):
        return None

    def insertTab(self, text, asHTML, beforeIndex=None):
        """ 1st arg can, instead of being 'text', be a widget.

            1st arg can also be None, which results in a blank
            space between tabs.  Use this to push subsequent
            tabs out to the right hand end of the TabBar.
            (the "blank" tab, by not being focussable, is not
            clickable).
        """
        if beforeIndex is None:
            beforeIndex = asHTML
            asHTML = False

        if (beforeIndex < 0) or (beforeIndex > self.getTabCount()):
            #throw new IndexOutOfBoundsException();
            pass

        if text is None:
            text = HTML("&nbsp;", True)
            text.setWidth("100%")
            text.setStyleName("gwt-TabBarRest")
            self.panel.insert(text, beforeIndex + 1)
            self.panel.setCellWidth(text, "100%")
            return

        try:
            istext = isinstance(text, str) or isinstance(text, unicode)
        except:
            istext = isinstance(text, str)

        if istext:
            if asHTML:
                item = HTML(text)
            else:
                item = Label(text)
            item.setWordWrap(False)
        else:
            # passing in a widget, it's expected to have its own style
            item = text

        self.insertTabWidget(item, beforeIndex)

    def insertTabWidget(self, widget, beforeIndex):

        delWidget = ClickDelegatePanel(self, widget, self, self)
        delWidget.setStyleName(self.STYLENAME_DEFAULT)

        focusablePanel = delWidget.getFocusablePanel()
        self.panel.insert(delWidget, beforeIndex + 1)

        self.setStyleName(DOM.getParent(delWidget.getElement()),
                          self.STYLENAME_DEFAULT + "-wrapper", True)

        #print "insertTabWidget", DOM.getParent(delWidget.getElement()), DOM.getAttribute(DOM.getParent(delWidget.getElement()), "className")


    def onClick(self, sender=None):
        for i in range(1, self.panel.getWidgetCount() - 1):
            if DOM.isOrHasChild(self.panel.getWidget(i).getElement(),
                                sender.getElement()):
                return self.selectTab(i - 1)
        return False

    def removeTab(self, index):
        self.checkTabIndex(index)

        toRemove = self.panel.getWidget(index + 1)
        if toRemove == self.selectedTab:
            self.selectedTab = None
        self.panel.remove(toRemove)

    def removeTabListener(self, listener):
        self.tabListeners.remove(listener)

    def selectTab(self, index):
        self.checkTabIndex(index)

        for listener in self.tabListeners:
            if not listener.onBeforeTabSelected(self, index):
                return False

        self.setSelectionStyle(self.selectedTab, False)
        if index == -1:
            self.selectedTab = None
            return True

        self.selectedTab = self.panel.getWidget(index + 1)
        self.setSelectionStyle(self.selectedTab, True)

        for listener in self.tabListeners:
            listener.onTabSelected(self, index)

        return True

    def checkTabIndex(self, index):
        if (index < -1) or (index >= self.getTabCount()):
            #throw new IndexOutOfBoundsException();
            pass

    def setSelectionStyle(self, item, selected):
        if item is not None:
            if selected:
                item.addStyleName("gwt-TabBarItem-selected")
                self.setStyleName(DOM.getParent(item.getElement()),
                                "gwt-TabBarItem-wrapper-selected", True)

            else:
                item.removeStyleName("gwt-TabBarItem-selected")
                self.setStyleName(DOM.getParent(item.getElement()),
                                "gwt-TabBarItem-wrapper-selected", False)

Factory.registerClass('pyjamas.ui.TabBar', TabBar)

