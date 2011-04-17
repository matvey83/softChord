"""
    Vertical Split Panel: Top and Bottom layouts with a movable splitter.

/*
 * Copyright 2008 Google Inc.
 * Copyright (C) 2008, 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
 * 
 * Licensed under the Apache License, Version 2.0 (the "License") you may not
 * use self file except in compliance with the License. You may obtain a copy of
 * the License at
 * 
 * http:#www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
"""

from splitpanel import SplitPanel
from pyjamas import Factory
from pyjamas import DOM
from pyjamas import DeferredCommand
from pyjamas.Timer import Timer
from __pyjamas__ import JS

class ImplVerticalSplitPanel:
    """ Provides a base implementation for splitter layout that relies on CSS
        positioned layout.
    """
    def __init__(self, panel):
        self.panel = panel

        DOM.setStyleAttribute(panel.getElement(), "position", "relative")

        topElem = panel.getWidgetElement(0)
        bottomElem = panel.getWidgetElement(1)

        self.expandToFitParentHorizontally(topElem)
        self.expandToFitParentHorizontally(bottomElem)
        self.expandToFitParentHorizontally(panel.getSplitElement())

        self.panel.expandToFitParentUsingCssOffsets(panel.container)

        # Snap the bottom wrapper to the bottom side.
        DOM.setStyleAttribute(bottomElem, "bottom", "0")

    def expandToFitParentHorizontally(self, elem):
        self.panel.addAbsolutePositoning(elem)
        DOM.setStyleAttribute(elem, "left", "0")
        DOM.setStyleAttribute(elem, "right", "0")

    def onAttach(self):
        pass

    def onDetach(self):
        pass

    def onSplitterResize(self, px):
        self.setSplitPosition(px)

    def setSplitPosition(self, px):
        splitElem = self.panel.getSplitElement()

        rootElemHeight = DOM.getOffsetHeight(self.panel.container)
        splitElemHeight = DOM.getOffsetHeight(splitElem)

        # layout not settled, set height to what it _should_ be... yuk.
        if splitElemHeight == 0:
            splitElemHeight = 7

        if rootElemHeight < splitElemHeight:
            return

        newBottomHeight = rootElemHeight - px - splitElemHeight
        if px < 0:
            px = 0
            newBottomHeight = rootElemHeight - splitElemHeight
        elif newBottomHeight < 0:
            px = rootElemHeight - splitElemHeight
            newBottomHeight = 0

        self.updateElements(self.panel.getWidgetElement(0),
                       splitElem,
                       self.panel.getWidgetElement(1),
                       px, px + splitElemHeight, newBottomHeight)

    def updateElements(self, topElem, splitElem,
                       bottomElem, topHeight, bottomTop, bottomHeight):
        self.panel.setElemHeight(topElem, "%dpx" % topHeight)
        self.panel.setTop(splitElem, "%dpx" % topHeight)
        self.panel.setTop(bottomElem, "%dpx" % bottomTop)
        # bottom's height is handled by CSS.

class ImplIE6VerticalSplitPanel:
    """ Provides an implementation for IE6/7 that relies on 100% length in CSS.
    """

    def __init__(self, panel):
        self.panel = panel
        self.isResizeInProgress = False
        self.isTopHidden = False
        self.isBottomHidden = False

        elem = panel.getElement()

        # Prevents inherited text-align settings from interfering with the
        # panel's layout.
        DOM.setStyleAttribute(elem, "textAlign", "left")
        DOM.setStyleAttribute(elem, "position", "relative")

        topElem = panel.getWidgetElement(0)
        bottomElem = panel.getWidgetElement(1)

        self.expandToFitParentHorizontally(topElem)
        self.expandToFitParentHorizontally(bottomElem)
        self.expandToFitParentHorizontally(panel.getSplitElement())

        self.expandToFitParentUsingPercentages(panel.container)

    def expandToFitParentHorizontally(self, elem):
        self.addAbsolutePositoning(elem)
        self.setLeft(elem, "0")
        self.setElemWidth(elem, "100%")

    def onAttach(self):
      self.addResizeListener(self.panel.container)
      self.onResize()

    def onDetach(self):
      DOM.setElementProperty(self.panel.container, "onresize", None)

    def onSplitterResize(self, px):
        """ IE6/7 has event priority issues that will prevent
            the repaints from happening quickly enough causing the
            interaction to seem unresponsive.  The following is simply
            a poor man's mouse event coalescing.
        """
        resizeUpdatePeriod = 20 # ms
        if not self.isResizeInProgress:
            self.isResizeInProgress = True
            Timer(resizeUpdatePeriod, self)
        self.splitPosition = px

    def onTimer(self, t):
        self.setSplitPosition(splitPosition)
        self.isResizeInProgress = False

    def updateElements(topElem, splitElem, bottomElem,
                        topHeight, bottomTop, bottomHeight):
        """ IE6/7 has a quirk where a zero height element with
            non-zero height children will expand larger than 100%. To
            prevent self, the width is explicitly set to zero when
            height is zero.
        """
        if topHeight == 0:
            self.setWidth(topElem, "0px")
            self.isTopHidden = True
        elif self.isTopHidden:
            self.setWidth(topElem, "100%")
            self.isTopHidden = False

        if bottomHeight == 0:
            self.setElemWidth(bottomElem, "0px")
            self.isBottomHidden = True
        elif self.isBottomHidden:
            self.setElemWidth(bottomElem, "100%")
            self.isBottomHidden = False

        self.panel.setElemHeight(topElem, "%dpx" % topHeight)
        self.panel.setTop(splitElem, "%dpx" % topHeight)
        self.panel.setTop(bottomElem, "%dpx" % bottomTop)
        # IE6/7 cannot update properly with CSS alone.
        self.panel.setElemHeight(bottomElem, bottomHeight + "px")

    def addResizeListener(self, container):
        JS("""
         this.container.onresize = function() {
               __ImplIE6VerticalSplitPanel_onResize();
                                   }
         """)

    def onResize(self):
        self.setSplitPosition(DOM.getOffsetHeight(self.panel.getWidgetElement(0)))

class VerticalSplitPanel(SplitPanel):
    """ A panel that arranges two widgets in a single vertical
        column and allows the user to interactively
        change the proportion of the height dedicated to
        each of the two widgets. Widgets contained within a
        <code>VerticalSplitterPanel</code> will be automatically
        decorated with scrollbars when necessary.
    """

    def __init__(self, **kwargs):
        """ Creates an empty vertical split panel.
        """
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-VerticalSplitPanel"
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createDiv()
        SplitPanel.__init__(self, element,
                            DOM.createDiv(),
                            self.preventBoxStyles(DOM.createDiv()),
                            self.preventBoxStyles(DOM.createDiv()),
                            **kwargs)

        self.container = self.preventBoxStyles(DOM.createDiv())
        self.buildDOM()

        self.impl = ImplVerticalSplitPanel(self)

        self.setSplitPosition("50%")

        # Captures the height of the top container when drag resizing starts.
        self.initialTopHeight = 0

        # Captures the offset of a user's mouse pointer during drag resizing.
        self.initialThumbPos = 0

        self.lastSplitPosition = ""

    def getBottomWidget(self):
        """ Gets the widget in the bottom of the panel.
            @return the widget, <code>None</code> if there is not one
        """
        return self.getWidget(1)

    def getTopWidget(self):
        """ Gets the widget in the top of the panel.
            @return the widget, <code>None</code> if there is not one
        """
        return self.getWidget(0)

    def setBottomWidget(self, w):
        """ Sets the widget in the bottom of the panel.
            @param w the widget
        """
        self.setWidget(1, w)

    def setSplitPosition(self, pos):
        self.lastSplitPosition = pos
        topElem = self.getWidgetElement(0)
        self.setElemHeight(topElem, pos)
        self.impl.setSplitPosition(DOM.getOffsetHeight(topElem))

    def setTopWidget(self, w):
        """ Sets the widget in the top of the panel.
            @param w the widget
        """
        self.setWidget(0, w)

    def onLoad(self):
        self.impl.onAttach()
        # Set the position realizing it might not work until
        # after layout runs.  This first call is simply to try
        # to avoid a jitter effect if possible.
        self.setSplitPosition(self.lastSplitPosition)
        DeferredCommand.add(self)

    def execute(self):
        self.setSplitPosition(self.lastSplitPosition)

    def onUnload(self):
        self.impl.onDetach()

    def onSplitterResize(self, x, y):
        self.impl.onSplitterResize(self.initialTopHeight + y -
                                   self.initialThumbPos)

    def onSplitterResizeStarted(self, x, y):
        self.initialThumbPos = y
        self.initialTopHeight = DOM.getOffsetHeight(self.getWidgetElement(0))

    def buildDOM(self):
        topDiv = self.getWidgetElement(0)
        bottomDiv = self.getWidgetElement(1)
        splitDiv = self.getSplitElement()

        DOM.appendChild(self.getElement(), self.container)

        DOM.appendChild(self.container, topDiv)
        DOM.appendChild(self.container, splitDiv)
        DOM.appendChild(self.container, bottomDiv)

        # The style name is placed on the table rather than splitElem
        # to allow the splitter to be styled without interfering
        # with layout.

        DOM.setInnerHTML(splitDiv, "<div class='vsplitter' " +
                                   "style='text-align:center'>" +
                                   self.getThumbImageHTML() + "</div>")

        self.addScrolling(topDiv)
        self.addScrolling(bottomDiv)

Factory.registerClass('pyjamas.ui.VerticalSplitPanel', VerticalSplitPanel)

