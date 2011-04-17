"""
    Horizontal Split Panel: Left and Right layouts with a movable splitter.

/*
 * Copyright 2008 Google Inc.
 * Copyright 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
 * 
 * Licensed under the Apache License, Version 2.0 (the "License") you may not
 * use this file except in compliance with the License. You may obtain a copy of
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

from __pyjamas__ import JS
from pyjamas import Factory
from splitpanel import SplitPanel
from pyjamas import DOM
from pyjamas import DeferredCommand

class ImplHorizontalSplitPanel:
    """ The standard implementation for horizontal split panels.
    """
    def __init__(self, panel):
        self.panel = panel

        DOM.setStyleAttribute(panel.getElement(), "position", "relative")

        self.expandToFitParentHorizontally(panel.getWidgetElement(0))
        self.expandToFitParentHorizontally(panel.getWidgetElement(1))
        self.expandToFitParentHorizontally(panel.getSplitElement())

        self.panel.expandToFitParentUsingCssOffsets(panel.container)

        # Right now, both panes are stacked on top of each other
        # on either the left side or the right side of the containing
        # panel. This happens because both panes have position:absolute 
        # and no left/top values. The panes will be on the left side 
        # if the directionality is LTR, and on the right side if the 
        # directionality is RTL. In the LTR case, we need to snap the 
        # right pane to the right of the container, and in the RTL case,
        # we need to snap the left pane to the left of the container.      

        if True: # TODO: (LocaleInfo.getCurrentLocale().isRTL()):
            self.panel.setLeft(self.panel.getWidgetElement(0), "0px")        
        else:
            self.panel.setRight(self.panel.getWidgetElement(1), "0px")

    def expandToFitParentHorizontally(self, elem):
      self.panel.addAbsolutePositoning(elem)
      zeroSize = "0px"
      self.panel.setTop(elem, zeroSize)
      self.panel.setBottom(elem, zeroSize)


    def onAttach(self):
        pass
    def onDetach(self):
        pass

    def onTimer(self, sender):
        pass
    def execute(self):
        pass
    def addResizeListener(self, container):
        pass
    def onResize(self):
        pass

    def onSplitterResize(self, px):
        self.setSplitPositionUsingPixels(px)

    def setSplitPosition(self, pos):
        leftElem = self.panel.getWidgetElement(0)
        self.panel.setElemWidth(leftElem, pos)
        self.setSplitPositionUsingPixels(DOM.getOffsetWidth(leftElem))

    def setSplitPositionUsingPixels(self, px):
        self._setSplitPositionUsingPixels(px)

    def _setSplitPositionUsingPixels(self, px):
        """ Set the splitter's position in units of pixels.
              
              px represents the splitter's position as a distance
              of px pixels from the left edge of the container. This is
              true even in a bidi environment. Callers of this method
              must be aware of this constraint.
        """
        splitElem = self.panel.getSplitElement()

        rootElemWidth = DOM.getOffsetWidth(self.panel.container)
        splitElemWidth = DOM.getOffsetWidth(splitElem)

        # This represents an invalid state where layout is incomplete. This
        # typically happens before DOM attachment, but I leave it here as a
        # precaution because negative width/height style attributes produce
        # errors on IE.
        if (rootElemWidth < splitElemWidth):
            return

        # Compute the new right side width.
        newRightWidth = rootElemWidth - px - splitElemWidth

        # Constrain the dragging to the physical size of the panel.
        if (px < 0):
            px = 0
            newRightWidth = rootElemWidth - splitElemWidth
        elif (newRightWidth < 0):
            px = rootElemWidth - splitElemWidth
            newRightWidth = 0

        rightElem = self.panel.getWidgetElement(1)

        # Set the width of the left side.
        self.panel.setElemWidth(self.panel.getWidgetElement(0), "%dpx" % px)

        # Move the splitter to the right edge of the left element.
        self.panel.setLeft(splitElem, "%dpx" % px)

        # Move the right element to the right of the splitter.
        self.panel.setLeft(rightElem, "%dpx" % (px + splitElemWidth))

        self.updateRightWidth(rightElem, newRightWidth)


    def updateRightWidth(self, rightElem, newRightWidth):
        # No need to update the width of the right side this will be
        # recomputed automatically by CSS. This is helpful, as we do not
        # have to worry about watching for resize events and adjusting the
        # right-side width.
        pass
  
class HorizontalSplitPanel(SplitPanel):
    """  A panel that arranges two widgets in a single horizontal row
         and allows the user to interactively change the proportion
         of the width dedicated to each of the two widgets. Widgets
         contained within a <code>HorizontalSplitPanel</code> will
         be automatically decorated with scrollbars when necessary.

         Default layout behaviour of HorizontalSplitPanels is to 100% fill
         its parent vertically and horizontally [this is NOT normal!]
    """

    def __init__(self, **kwargs):
        """ Creates an empty horizontal split panel.
        """

        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-HorizontalSplitPanel"

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

        self.impl = ImplHorizontalSplitPanel(self)

        # By default the panel will fill its parent vertically and horizontally.
        # The horizontal case is covered by the fact that the top level div is
        # block display.
        self.setHeight("100%")

        self.lastSplitPosition = "50%"
        self.initialLeftWidth = 0
        self.initialThumbPos = 0

    def add(self, w):
        """
           * Adds a widget to a pane in the HorizontalSplitPanel. The method
           * will first attempt to add the widget to the left pane. If a 
           * widget is already in that position, it will attempt to add the
           * widget to the right pane. If a widget is already in that position,
           * an exception will be thrown, as a HorizontalSplitPanel can
           * contain at most two widgets.
           * 
           * Note that this method is bidi-sensitive. In an RTL environment,
           * this method will first attempt to add the widget to the right pane,
           * and if a widget is already in that position, it will attempt to add
           * the widget to the left pane.
           * 
           * @param w the widget to be added
           * @throws IllegalStateException
        """
        if self.getStartOfLineWidget() is None:
            self.setStartOfLineWidget(w)
        elif self.getEndOfLineWidget() is None:
            self.setEndOfLineWidget(w)
        else:
            return
          # TODO throw new IllegalStateException(
          #    "A Splitter can only contain two Widgets.")

    def getEndOfLineWidget(self):
        """
           * Gets the widget in the pane that is at the end of the line
           * direction for the layout. That is, in an RTL layout, gets
           * the widget in the left pane, and in an LTR layout, gets
           * the widget in the right pane.
           *
           * @return the widget, <code>null</code> if there is not one.
        """
        return self.getWidget(self.getEndOfLinePos())
   
    def getLeftWidget(self):
        """
           * Gets the widget in the left side of the panel.
           * 
           * @return the widget, <code>null</code> if there is not one.
        """
        return self.getWidget(0)

    def getRightWidget(self):
        """
           * Gets the widget in the right side of the panel.
           * 
           * @return the widget, <code>null</code> if there is not one.
        """
        return self.getWidget(1)

    def getStartOfLineWidget(self):
        """
        * Gets the widget in the pane that is at the start of the line 
        * direction for the layout. That is, in an RTL environment, gets
        * the widget in the right pane, and in an LTR environment, gets
        * the widget in the left pane.   
        *
        * @return the widget, <code>null</code> if there is not one.
        """
        return self.getWidget(self.getStartOfLinePos())

    def setEndOfLineWidget(self, w):
        """
       * Sets the widget in the pane that is at the end of the line direction
       * for the layout. That is, in an RTL layout, sets the widget in
       * the left pane, and in and RTL layout, sets the widget in the 
       * right pane.
       *
       * @param w the widget
        """
        self.setWidget(self.getEndOfLinePos(), w)

    def setLeftWidget(self, w):
        """
           * Sets the widget in the left side of the panel.
           * 
           * @param w the widget
        """
        self.setWidget(0, w)

    def setRightWidget(self, w):
        """
           * Sets the widget in the right side of the panel. 
           * 
           * @param w the widget
        """
        self.setWidget(1, w)
 
    def setSplitPosition(self, pos):
        """
       * Moves the position of the splitter.
       *
       * This method is not bidi-sensitive. The size specified is always
       * the size of the left region, regardless of directionality.
       *
       * @param pos the new size of the left region in CSS units (e.g. "10px",
       *             "1em")
        """
        self.lastSplitPosition = pos
        self.impl.setSplitPosition(pos)

    def setStartOfLineWidget(self, w):
        """
       * Sets the widget in the pane that is at the start of the line direction
       * for the layout. That is, in an RTL layout, sets the widget in
       * the right pane, and in and RTL layout, sets the widget in the
       * left pane.
       *
       * @param w the widget
        """
        self.setWidget(self.getStartOfLinePos(), w)

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
        self.lastSplitPosition = x
        self.impl.onSplitterResize(self.initialLeftWidth + x -
                                   self.initialThumbPos)

    def onSplitterResizeStarted(self, x, y):
        self.initialThumbPos = x
        self.initialLeftWidth = DOM.getOffsetWidth(self.getWidgetElement(0))


    def buildDOM(self):

        leftDiv = self.getWidgetElement(0)
        rightDiv = self.getWidgetElement(1)
        splitDiv = self.getSplitElement()

        DOM.appendChild(self.getElement(), self.container)

        DOM.appendChild(self.container, leftDiv)
        DOM.appendChild(self.container, splitDiv)
        DOM.appendChild(self.container, rightDiv)

        # Sadly, this is the only way I've found to get vertical
        # centering in this case. The usually CSS hacks (display:
        # table-cell, vertical-align: middle) don't work in an
        # absolute positioned DIV.
        DOM.setInnerHTML(splitDiv,
            "<table class='hsplitter' height='100%' cellpadding='0' " +
                "cellspacing='0'><tr><td align='center' valign='middle'>" +
                self.getThumbImageHTML() +
                "</td></tr></table>")

        self.addScrolling(leftDiv)
        self.addScrolling(rightDiv)

    def getEndOfLinePos(self):
        return 0
        # TODO: return (LocaleInfo.getCurrentLocale().isRTL() ? 0 : 1)
  
    def getStartOfLinePos(self):
        return 1
        # TODO: return (LocaleInfo.getCurrentLocale().isRTL() ? 1 : 0)

Factory.registerClass('pyjamas.ui.HorizontalSplitPanel', HorizontalSplitPanel)

