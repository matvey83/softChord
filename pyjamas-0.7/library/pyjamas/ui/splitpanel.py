"""
/*
 * Copyright 2008 Google Inc.
 * Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
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
from Panel import Panel
from pyjamas import Factory
from pyjamas.ui import Event

from pyjamas import DOM

class SplitPanel(Panel):
    """ Abstract base class for {@link HorizontalSplitPanel} and
        {@link VerticalSplitPanel}.
    """

    def __init__(self, mainElem, splitElem, headElem, tailElem, **kwargs):
        """ Initializes the split panel.
           @param mainElem the root element for the split panel
           @param splitElem the element that acts as the splitter
           @param headElem the element to contain the top or left most widget
           @param tailElem the element to contain the bottom or right most widget
        """

        self.widgets = [None, None]
        self.elements = [headElem, tailElem]
        self.isResizing = False

        self.setElement(mainElem)
        self.splitElem = splitElem

        if not kwargs.has_key('ThumbImage'):
            kwargs['ThumbImage'] = "splitPanelThumb.png"

        Panel.__init__(self, **kwargs)

        self.sinkEvents(Event.MOUSEEVENTS)

    def setThumbImage(self, ti):
        self.thumb_image = ti

    def getThumbImageHTML(self):
        if self.thumb_image:
             return '<img src="%s" />' % self.thumb_image
        return ""

    def addAbsolutePositoning(self, elem):
        """ Sets an elements positioning to absolute.
        """
        DOM.setStyleAttribute(elem, "position", "absolute")

    def addClipping(self, elem):
        """ Adds clipping to an element.
        """
        DOM.setStyleAttribute(elem, "overflow", "hidden")

    def addScrolling(self, elem):
        """ Adds as-needed scrolling to an element.
        """
        DOM.setStyleAttribute(elem, "overflow", "auto")

    def expandToFitParentUsingCssOffsets(self, elem):
        """ Sizes and element to consume the full area of its parent
            using the CSS properties left, right, top, and
            bottom. This method is used for all browsers except IE6/7.
        """
        zeroSize = "0px"

        self.addAbsolutePositoning(elem)
        self.setLeft(elem, zeroSize)
        self.setRight(elem, zeroSize)
        self.setTop(elem, zeroSize)
        self.setBottom(elem, zeroSize)

    def expandToFitParentUsingPercentages(self, elem):
        """ Sizes an element to consume the full areas of its parent
            using 100% width and height. This method is used on IE6/7
            where CSS offsets don't work reliably.
        """
        zeroSize = "0px"
        fullSize = "100%"

        self.addAbsolutePositoning(elem)
        self.setTop(elem, zeroSize)
        self.setLeft(elem, zeroSize)
        self.setElemWidth(elem, fullSize)
        self.setElemHeight(elem, fullSize)

    def preventBoxStyles(self, elem):
        """ Adds zero or none CSS values for padding, margin and
            border to prevent stylesheet overrides. Returns the
            element for convenience to support builder pattern.
        """
        DOM.setIntStyleAttribute(elem, "padding", 0)
        DOM.setIntStyleAttribute(elem, "margin", 0)
        DOM.setStyleAttribute(elem, "border", "none")
        return elem

    def setBottom(self, elem, size):
        """ Convenience method to set bottom offset of an element.
        """
        DOM.setStyleAttribute(elem, "bottom", size)

    def setElemHeight(self, elem, height):
        """ Convenience method to set the height of an element.
        """
        DOM.setStyleAttribute(elem, "height", height)

    def setLeft(self, elem, left):
        """ Convenience method to set the left offset of an element.
        """
        DOM.setStyleAttribute(elem, "left", left)

    def setRight(self, elem, right):
        """ Convenience method to set the right offset of an element.
        """
        DOM.setStyleAttribute(elem, "right", right)

    def setTop(self, elem, top):
        """ Convenience method to set the top offset of an element.
        """
        DOM.setStyleAttribute(elem, "top", top)

    def setElemWidth(self, elem, width):
        """ Convenience method to set the width of an element.
        """
        DOM.setStyleAttribute(elem, "width", width)

    def add(self, w):
        if self.getWidget(0) is None:
            self.setWidget(0, w)
        elif self.getWidget(1) is None:
            self.setWidget(1, w)
        #else:
        #    raise IllegalStateException("A Splitter can only contain two Widgets.")

    def isResizing(self):
        """ Indicates whether the split panel is being resized.

            @return <code>True</code> if the user is dragging the splitter,
                    <code>False</code> otherwise
        """
        return self.isResizing

    def __iter__(self):
        return self.widgets.__iter__()

    def onBrowserEvent(self, event):
        typ = DOM.eventGetType(event)

        if typ == "mousedown":
            target = DOM.eventGetTarget(event)
            if DOM.isOrHasChild(self.splitElem, target):
                self.startResizingFrom(DOM.eventGetClientX(event) -
                                       self.getAbsoluteLeft(),
                          DOM.eventGetClientY(event) - self.getAbsoluteTop())
                DOM.setCapture(self.getElement())
                DOM.eventPreventDefault(event)

        elif typ == "mouseup":
            DOM.releaseCapture(self.getElement())
            self.stopResizing()

        elif typ == 'mousemove':
            if self.isResizing:
                #assert DOM.getCaptureElement() is not None
                self.onSplitterResize(DOM.eventGetClientX(event) -
                                      self.getAbsoluteLeft(),
                          DOM.eventGetClientY(event) - self.getAbsoluteTop())
                DOM.eventPreventDefault(event)

    def remove(self, widget):
        if widgets[0] == widget:
            setWidget(0, None)
            return True
        elif widgets[1] == widget:
            setWidget(1, None)
            return True
        return False

    def setSplitPosition(self, size):
        """ Moves the position of the splitter.
            @param size the new size of the left region in CSS units
            (e.g. "10px", "1em")
        """
        pass

    def getWidgetElement(self, index):
        """ Gets the content element for the given index.
            @param index the index of the element, only 0 and 1 are valid.
            @return the element
        """
        return self.elements[index]

    def getSplitElement(self):
        """ Gets the element that is acting as the splitter.
            @return the element
        """
        return self.splitElem

    def getWidget(self, index):
        """ Gets one of the contained widgets.
            @param index the index of the widget, only 0 and 1 are valid.
            @return the widget
        """
        return self.widgets[index]

    def setWidget(self, index, w):
        """ Sets one of the contained widgets.
            @param index the index, only 0 and 1 are valid
            @param w the widget
        """
        oldWidget = self.widgets[index]

        if oldWidget == w:
          return

        if w is not None:
          w.removeFromParent()

        # Remove the old child.
        if oldWidget is not None:
          # Orphan old.
          self.disown(oldWidget)
          # Physical detach old.
          #DOM.removeChild(self.elements[index], oldWidget.getElement())

        # Logical detach old / attach new.
        self.widgets[index] = w

        if w is not None:
            # Physical attach new.
            DOM.appendChild(self.elements[index], w.getElement())

            # Adopt new.
            self.adopt(w, None)

    def onSplitterResize(self, x, y):
        """ Called on each mouse drag event as the user is dragging
            the splitter.
            @param x the x coord of the mouse relative to the panel's extent
            @param y the y coord of the mosue relative to the panel's extent
        """
        pass

    def onSplitterResizeStarted(self, x, y):
        """ Called when the user starts dragging the splitter.
            @param x the x coord of the mouse relative to the panel's extent
            @param y the y coord of the mouse relative to the panel's extent
        """

    def startResizingFrom(self, x, y):
        self.isResizing = True
        self.onSplitterResizeStarted(x, y)

    def stopResizing(self):
        self.isResizing = False

# TODO: this is really an internal base class for Horizontal and Vertical
# SplitPanels?
#Factory.registerClass('pyjamas.ui.SplitPanel', SplitPanel)

