"""
* Copyright 2007,2008,2009 John C. Gunther
* Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
*
* Licensed under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License. You may obtain a copy of the License at:
*
*  http:#www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the specific
* language governing permissions and limitations under the
* License.
*
"""


import math

from pyjamas import DOM
from pyjamas import Window


from pyjamas.ui import Event
from pyjamas.ui.AbsolutePanel import AbsolutePanel
from pyjamas.ui.Composite import Composite
from pyjamas.ui.Grid import Grid
from pyjamas.ui import HasHorizontalAlignment
from pyjamas.ui import HasVerticalAlignment
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Image import Image
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.UIObject import UIObject
from pyjamas.ui.Widget import Widget

from pyjamas.chart.GChartConsts import N_PRE_SYSTEM_CURVES
from pyjamas.chart.GChartConsts import TRANSPARENT_BORDER_COLOR
from pyjamas.chart.GChartConsts import HOVER_ANNOTATION_ID
from pyjamas.chart.GChartConsts import HOVER_CURSOR_ID
from pyjamas.chart.GChartConsts import USE_CSS
from pyjamas.chart.GChartConsts import NAI
from pyjamas.chart.GChartConsts import DEFAULT_BLANK_IMAGE_URL_FULLPATH

from pyjamas.chart import GChartUtil
from pyjamas.chart import Double

from pyjamas import log

"""
* This class' sole purpose is to work around a FF 2
* performance limitation: chart update times increase as
* O(N^2) after the number of direct ancestor child widgets in
* a single AbsolutePanel exceeds around 500-1000, AND the
* chart is updated in more than one browser-displayed stage
* (e.g, via a series of incremental updates that successively
* add more curve data, for purposes of user feedback). By
* contrast, IE7 times grow as O(N) even if 3,000 child widgets
* are added to a previously displayed chart (e.g. by adding a
* bar curve with 3,000 bars on it).
*
* <p>
*
* For solid-fill line chart support (LINE SymbolType
* introduced in 2.2), thousands of widgets are often needed
* and so these O(N^2) FF 2 times were just too slow.
*
* <p>
*
* Some kind of fixed hash table inside of FF 2 divs could
* explain this switch from O(N) to O(N^2) performance.
* <p>
*
* Approach is to split up the large AbsolutePanel into a
* series of child panels, each of which contains a number of
* elements within the range where FF 2 updates are O(N).
* <p>
*
* Tried to keep it light-weight so IE7 isn't penalized too
* much for having to workaround this FF 2 limitation.
*
"""

WIDGETS_PER_PANEL = 256

class PartitionedAbsolutePanel (Composite):
    """ Max number of widgets in each panel; chose a value as large as
    possible while remaining within the empirically
    determined FF 2 O(N) range. Here's the data (from a 3,000 element
    test based on the sin curve of the 2.1 live demo
    called GChartExample15c.java) upon which this choice was based:
    <p>

    <pre>

    Size    FF2    IE7
    (sec)  (sec)
    1     ~14     16
    2      11     13
    32      9      11
    64      9      12
    128      9      11
    256      9      11
    512      10     11
    1024     15     11
    2048     27     11
    4096*    61     12

    </pre>
    <p>

    The two largest sizes are good approximations of FF2 times we got
    informally before the switch to partitioned AbsolutePanels with
    charts with the corresponding number of elements (2000 or 3000).
    The overhead of the partitioning itself is very low, as shown by
    the modest time increase even when each element is placed into
    its own sub-panel. Tests with a < 256 element chart suggested at
    most a couple of ms of time increases due to the introduction of
    partitioning.

    <p>

    I kind of expected to see >61 second times with a sub-panel size
    of 1, since the parent panel still has >3,000 elements in this
    case. Whatever the cause of the performance logjam (presumably in
    the FF2 heap somewhere?)  simply the fact that you introduce a
    parent AbsolutePanel that holds various child AbslolutePanels
    that hold the actual image widgets appears to work around most of
    the problem. If such a useless change makes FF2 materially
    faster, that seems like a performance bug in FF2 to me.<p>

    The root FF cause is apparently NOT image cache related, though,
    since turning off the image cache via about:config didn't change
    times for the last row of the table above.

    """

    """ Strange, reorganized DOM layout in GChart v2.5 and now cannot
    * reproduce these results in FF2 (partitioning gave just a modest 1
    * second boost in a 15 second, 4,000 point test). So, I was about to
    * drop back to a simple AbsolutePanel. BUT, in FF3, now, the 4,000
    * point test crashes unless I use PartitionedAbsolutePanel! I guess
    * Firefox 3 has problems with divs that have 4,000 elements, or at
    * least 4,000 image elements, on them, which the partioning fixes.
    *
    """

    def __init__(self, **kwargs):
        self.root = AbsolutePanel()
        self.subPanel = None # "selected" subPanel
        self.iSubPanel = -1    # index of "selected" subPanel
        self.nWidgets = 0;     # total # over all subPanels

        Composite.__init__(self, **kwargs)
        self.initWidget(self.root)


    """ resets the partitioned panel to its initial state """
    def clear(self):
        self.root.clear()
        self.subPanel = None
        self.iSubPanel = -1
        self.nWidgets = 0


    def getWidgetCount(self):
        return self.nWidgets


    # makes the subpanel containing the widget the selected one.
    def selectSubPanel(self, iWidget):
        if self.iSubPanel != int(iWidget/WIDGETS_PER_PANEL):
            self.iSubPanel = int(iWidget/WIDGETS_PER_PANEL)
            self.subPanel = self.root.getWidget(self.iSubPanel)



    # adds a widget to end of this partioned absolute panel
    def add(self, w):
        if (self.nWidgets % WIDGETS_PER_PANEL) == 0:
            # last panel is full, time to add a one
            self.subPanel = AbsolutePanel()
            # Panel sits in upper left corner. Does nothing, can't
            # be seen. It's just a holder for other widgets.
            GChartUtil.setOverflow(self.subPanel, "visible")
            self.subPanel.setPixelSize(0,0)
            self.root.add(self.subPanel, 0, 0)

        self.selectSubPanel(self.nWidgets)
        self.subPanel.add(w)
        self.nWidgets += 1


    # returns widget at given index
    def getWidget(self, iWidget):
        if iWidget < 0  or  iWidget >= self.nWidgets:
            raise IndexError(
                    "Invalid widget index: " + str(iWidget) +
                    ". Valid range is: 0..." + str((self.nWidgets-1)))

        self.selectSubPanel(iWidget)
        result = self.subPanel.getWidget( iWidget % WIDGETS_PER_PANEL)
        return result


    # Remove very last widget from panel.
    def remove(self, iWidget):
        if iWidget != self.nWidgets-1:
            raise IllegalArgumentException(
            "iWidgets arg = " + iWidget + " nWidgets-1 (" + (self.nWidgets-1)+") is required.")

        self.selectSubPanel(iWidget)
        result = self.subPanel.remove(iWidget % WIDGETS_PER_PANEL)
        if (iWidget % WIDGETS_PER_PANEL) == 0:
            # if deleted widget is last widget overall, and first on
            # the selected panel, selected panel will now be empty.
            self.root.remove(self.subPanel)
            self.iSubPanel = -1    # next selectSubPanel will reset these
            self.subPanel = None

        self.nWidgets -= 1
        return result




    # To assure that w is on the selected subPanel, this method
    # must only be passed a widget that is in the currently
    # selected subPanel. This can be assured by passing in a
    # widget that was just added via add(), or just retrieved
    # via getWidget (otherwise, an exception will be thrown).

    def setWidgetPosition(self, w, left, top):
        self.subPanel.setWidgetPosition(w, left, top)


 # end of class PartitionedAbsolutePanel

class AlignedLabel(Grid):
    def __init__(self, **kwargs):
        Grid.__init__(self, 1, 1, **kwargs)
        self.getCellFormatter().setWordWrap(0,0,False)
        self.setCellPadding(0)
        self.setCellSpacing(0)
        self.setBorderWidth(0)





class Rectangle(object):
    # a (pixel graphics coords) rectangle
    def __str__(self):
        return "Rect <%fx%f,%f-%f>" % (self.x, self.y, self.width, self.height)
    #double x;  # x, y at upper left corner of rectangle
    #double y
    #double width;  # distance from x to right edge
    #double height; # distance from y to bottom edge

"""*
* Provides support for reusing certain property specifications
* that are likely to be the same, given how aligned labels in a
* GChart get reused, and given certain assumptions about which
* properties of the labels are most likely to remain unchanged
* between updates.
* <p>
*
* Also applies a hidden outter grid technique to allow proper
* alignment with labels of unknown size without occluding
* mouse events of nearby elements.
* <p>
*
* Very similar in intent to the ReusableImage, see that
* class' header comment for more info.
*
"""
class NonoccludingReusuableAlignedLabel (AlignedLabel):
    def getInnerGrid(self):
        return self.innerGrid

    def __init__(self):
        self.fontSize = NAI
        self.fontStyle = USE_CSS
        self.fontWeight = USE_CSS
        self.fontColor = USE_CSS
        self.labelText = None
        self.isHTML = False
        self.labelWidget = None
        self.innerGrid = AlignedLabel()
        self.hAlign = None
        self.vAlign = None

        AlignedLabel.__init__(self)

        self.setWidget(0, 0, self.innerGrid)
        """
        * The basic technique being used in the lines below is
        * illustrated by this excerpt from p 317 of "CSS, The
        * Definitive Guide" by Eric A. Meyer: <p>
        *
        * <pre>
        *   p.clear {visibility: hidden;}
        *   p.clear em {visibility: visible;}
        * </pre>
        * <p>
        *
        * In the above example, emphasized (italic) text is
        * positioned exactly as it would have been in the
        * paragraph had the normal text been visible, except that
        * the normal text <i>isn't</i> visible. And, unlike
        * transparent text, the invisible text also won't capture
        * mouse events (essential for our aligned labels)
        *
        * <p>
        *
        * With GChart's aligned label, we want the outter Grid (HTML
        * table) to be "not there" as far as visibility and
        * mouseovers, but still impact centering and
        * other alignment of the stuff in the visible, inner Grid.
        *
        * <p>
        *
        * Note that we cannot just make the Grid color transparent
        * (tried that first) because in that case the oversized
        * outter Grid required for alignment will still grab the
        * mouseover events inappropriately (wrong hovertext
        * problem).
        *
        * <p>
        *
        * Not certain but, apparently, IE6 requires that, if
        * you want to apply this trick when the outer element
        * is a table you must use another table as the
        * inner element. At least, the div inner element approach
        * I used at first (that basically worked in Firefox), made
        * both parent and child invisible in IE6.
        * <p>
        *
        * In summary:
        *
        * The upside: alignment without inappropriate event occlusion
        * The downside: the extra Grid element saps performance
        *
        """

        DOM.setStyleAttribute(self.getElement(), "visibility","hidden")
        DOM.setStyleAttribute(self.innerGrid.getElement(),
                              "visibility", "visible")


    """
    * Sets properties only if they have changed; to replace
    * expensive DOM calls with cheap inequality tests.
    *
    * TODO: Investigate moving properties that are guaranteed to be
    * the same across all elements in the image panel (backgroundColor,
    * borderColor, borderWidth, borderStyle, image url, possibly more)
    * into a single style for the image panel as a whole, and just add
    * that styleName to each image, and set the properties once, in
    * the style. If this worked, it would save both time and space
    * (style would be internal and not intended for direct developer
    * access, since in some charts canvas, not styles, would be
    * responsible for these curve properties), and the same approach
    * could be applied to the labelPanel.
    *
    """

    def setReusableProperties(self, fontSize, fontStyle, fontWeight, fontColor,
                                    hAlign, vAlign, labelText,
                                    isHTML, labelWidget):

        if self.fontSize != fontSize:
            DOM.setIntStyleAttribute(self.innerGrid.getElement(), "fontSize", fontSize)
            self.fontSize = fontSize

        if self.fontStyle != fontStyle:
            DOM.setStyleAttribute(self.innerGrid.getElement(), "fontStyle", fontStyle)
            self.fontStyle = fontStyle

        if self.fontWeight != fontWeight:
            DOM.setStyleAttribute(self.innerGrid.getElement(), "fontWeight", fontWeight)
            self.fontWeight = fontWeight

        if self.fontColor != fontColor:
            DOM.setStyleAttribute(self.innerGrid.getElement(),"color", fontColor)
            self.fontColor = fontColor

        if self.hAlign != hAlign:
            self.getCellFormatter().setHorizontalAlignment(0,0,hAlign)
            # without this, only IE6-quirks doesn't quite align right:
            self.innerGrid.getCellFormatter().setHorizontalAlignment(0,0,hAlign)
            self.hAlign = hAlign

        if self.vAlign != vAlign:
            self.getCellFormatter().setVerticalAlignment(0,0,vAlign)
            # without this, only IE6-quirks doesn't quite align right:
            self.innerGrid.getCellFormatter().setVerticalAlignment(0,0,vAlign)
            self.vAlign = vAlign


        if None != labelWidget:
            if self.labelWidget != labelWidget:
                self.innerGrid.setWidget(0,0,labelWidget)
                self.labelWidget = labelWidget
                self.labelText = None


        elif self.labelText != labelText  or  self.isHTML != isHTML:
            if None == labelText  or  "" == labelText:
                self.innerGrid.setText(0,0,"")

            elif not isHTML:
                self.innerGrid.setText(0,0,labelText)

            else:
                self.innerGrid.setHTML(0, 0, labelText)

            self.isHTML = isHTML
            self.labelText = labelText
            self.labelWidget = None


 # end of class NonoccludingReusuableAlignedLabel

"""
* AbsolutePanel that allows annotations it contains to be easily
* reused, for increased efficiency.
*
"""
class AnnotationRenderingPanel (PartitionedAbsolutePanel):
    """
    * Returns the inner grid of the first reusuable, non-occluding
    * aligned label in this rendering panel.
    *
    """
    def getFirstInnerAlignedLabel(self):
        result = None
        if self.labelIndex > 0:
            parent = self.getWidget(0)
            result = parent.getInnerGrid()

        return result


    def __init__(self, chart):
        self.chart = chart
        self.labelIndex = 0;                # to-be-added-next label index
        self.lastVisibleLabel = -1; # just before 1st valid index
        PartitionedAbsolutePanel.__init__(self)
        """
        * Because of event-occlusion that can occur on all browsers but IE,
        * annotation panels MUST by 0-sized/overflow:visible otherwise they
        * will short-circuit event processing needed for widget annotations
        * added by developer. Graphics rendering panels don't have this
        * constraint and thus can be clipped to the plot area.
        *
        """
        GChartUtil.setOverflow(self, "visible")
        self.setPixelSize(0,0)


    def setLabelPosition(self, lbl, x, y):
        # workaround problem with special meaning of (-1,-1) to
        # setWidgetPosition (makes position off by one pixel).
        if x == -1  and  y == -1:
            x = 0

        self.setWidgetPosition(lbl, x, y)


    def beginRendering(self):
        self.labelIndex = 0


    def endRendering(self):
        # hide or remove labels no longer being used
        if self.chart.optimizeForMemory:
            iLabel = (self.getWidgetCount()-1)
        else:
            iLabel = self.lastVisibleLabel
        while iLabel >= self.labelIndex:
            w = self.getWidget(iLabel)
            if self.chart.optimizeForMemory:
                self.remove(iLabel)
            else:
                w.setVisible(False)
            iLabel -= 1

        self.lastVisibleLabel = self.labelIndex-1


    """
    * Creates (or reveals), and configures, an aligned label. Works
    * very similarly to addOrRevealImage.
    *
    """
    def getNextOrNewAlignedLabel(self, fontSize, fontStyle, fontWeight, fontColor, hAlign, vAlign, labelText, isHTML, labelWidget):
        if self.labelIndex < self.getWidgetCount():
            result = self.getWidget(self.labelIndex)
            if None != result.labelWidget  and  labelWidget == result.labelWidget:
                """
                * DOM element actually stored in the label's Grid-cell, and what
                * the label "thinks" is stored there, could be inconsistent if,
                * for example, the same label widget reference was used to
                * define two different points' annotations. In that case, we
                * need to clear the widget reference that the label stores
                * thus making it consistent with what is really in the DOM.
                * <p>
                *
                * This code was added to fix the bug reproduced by
                * TestGChart53.java. See that test for more info.
                *
                *
                """
                e = labelWidget.getElement()
                if (None == e  or  
                    (DOM.getParent(e) != 
                     result.innerGrid.getCellFormatter().getElement(0,0))):
                    # the widget' DOM parent isn't label's grid-cell (it was moved)
                    result.labelWidget = None



            if self.labelIndex > self.lastVisibleLabel:
                result.setVisible(True)


        else:
            result = NonoccludingReusuableAlignedLabel()
            self.add(result)

        result.setReusableProperties(fontSize, fontStyle, fontWeight,
                                    fontColor, hAlign, vAlign,
                                    labelText, isHTML, labelWidget)

        if self.lastVisibleLabel < self.labelIndex:
            self.lastVisibleLabel = self.labelIndex

        self.labelIndex += 1
        return result


    def renderAnnotation(self, annotation, loc, xCenter, yCenter, symWidth, symHeight, symbol):

        widthUpperBound = annotation.getWidthUpperBound()
        upLeftX = loc.getUpperLeftX(xCenter, widthUpperBound, abs(symWidth))
        heightUpperBound = annotation.getHeightUpperBound()
        upLeftY = loc.getUpperLeftY(yCenter, heightUpperBound, abs(symHeight))


        alignedLabel = self.getNextOrNewAlignedLabel(
                                    annotation.getFontSize(),
                                    annotation.getFontStyle(),
                                    annotation.getFontWeight(),
                                    annotation.getFontColor(),
                                    loc.getHorizontalAlignment(),
                                    loc.getVerticalAlignment(),
                                    annotation.getText(), annotation.isHTML(),
                                    annotation.getWidget())
        # If positioning by top or left edges, explicit sizing isn't needed
        # (makes the bounding box tighter, which, for reasons unknown, makes
        # rendering around 10% faster on some browsers and usage scenarios).
        if loc.getHorizontalAlignment() != HasHorizontalAlignment.ALIGN_LEFT:
            alignedLabel.setWidth(str(widthUpperBound) + "px")

        else:
            alignedLabel.setWidth("")


        if loc.getVerticalAlignment() != HasVerticalAlignment.ALIGN_TOP:
            alignedLabel.setHeight(str(heightUpperBound) + "px")

        else:
            alignedLabel.setHeight("")


        self.setLabelPosition(alignedLabel, upLeftX, upLeftY)



 # end of class AnnotationRenderingPanel

"""*
* Provides support for reusing certain property specifications
* that are likely to be the same, given how images in a GChart
* get reused, and given certain assumptions about which
* properties of the image are most likely to remain unchanged
* between updates.  For the most common scenarios, chart
* updates are significantly faster due to replacing (relatively
* expensive) DOM style attribute setting with (relatively
* cheap) String reference or integer equality tests.
* <p>
*
* For hovertext, the class also lets us defer actual generation
* of the hovertext until they actually mouse over the image,
* saving further time (it's surprisingly expensive just to
* format the numbers and such used in hovertexts).
* <p>
*
* TODO: Since we no longer use events on Image widgets,
* see if we can switch to just using simpler HTML elements,
* if that reduces the overhead associated with a Widget?
*
*
"""
class ReusableImage (Image):
    def __init__(self, parent):
        self._parent = parent
        self.backgroundColor = USE_CSS
        self.borderColor = USE_CSS
        self.borderStyle = USE_CSS
        # the capped border width, times two (to allow half-pixel widths)
        self.cappedBorderWidthX2 = NAI
        self.width = NAI
        self.height = NAI
        self.x = NAI
        self.y = NAI
        self.url = None

        Image.__init__(self)


    def setReusableProperties(self, backgroundColor, borderColor, borderStyle, borderWidth, dWidth, dHeight, xD, yD, url):

        # Round two edges, and define width to be their difference.
        # (rounding this way assures bars align with gridlines, etc.)
        newX = int ( round(xD) )
        newW = int ( round(xD + dWidth) - newX )
        newY = int ( round(yD) )
        newH = int ( round(yD + dHeight) - newY )
        thickness = min(newW, newH) 
        # Don't allow borders that would exceed specified width or
        # height. So, if smaller of width, height is at least twice the
        # border width, border width is used as is, otherwise,
        # it's replaced with half the smaller of width, height:
        newCappedBorderWidthX2 = min (2*borderWidth, thickness) 

        """
        * Note: on a GWT absolute panel, the x,y position of the widget is the
        * upper left corner of the widget's border, so x, y need no adjustment
        * to account for an internal (positive) border. Negative (external)
        * borders expand rectangle equally in all directions, so x,y need to
        * shift back to the upper left corner.  Transparent border
        * emulation sets border width to 0, and adjusts element size and
        * position to mimic border transparency (this rather odd feature is
        * required to workaround the IE6 "transparent border" bug)
        *
        """
        if TRANSPARENT_BORDER_COLOR == borderColor:
            #transparency emulation
            if newCappedBorderWidthX2 > 0:
                # to emulate an internal transparent border using a 0 width
                # border, we need to shift the upper left corner by the
                # amount of border, and shrink the size by twice the amount
                # of the border.
                newX += newCappedBorderWidthX2/2; # shift upper left corner
                newY += newCappedBorderWidthX2/2
                newH -= newCappedBorderWidthX2; # shrink size
                newW -= newCappedBorderWidthX2

            # else, external border is just eliminated, no adjustment needed
            newCappedBorderWidthX2 = 0
            borderColor = "transparent"; # because DOM won't accept None
            if backgroundColor == TRANSPARENT_BORDER_COLOR:
                backgroundColor = "transparent"


        elif newCappedBorderWidthX2 < 0:
            newX += newCappedBorderWidthX2/2; # shift upper left corner back
            newY += newCappedBorderWidthX2/2; # to incorporate external border.

        else:
            newH -= newCappedBorderWidthX2; # shrink size to incorporate
            newW -= newCappedBorderWidthX2; # impact of internal border.


        if self.cappedBorderWidthX2 != newCappedBorderWidthX2:
            if 1 == (newCappedBorderWidthX2 % 2):
                # odd pixel 2 x borderWidth needs asymetical borders to fill rect
                # (only positive (internal) borders can have half-pixel widths)
                floorBW = int(newCappedBorderWidthX2/2)
                ceilBW = floorBW+1
                # (top, right, bottom, left) == (floor, floor, ceil, ceil)
                # assures symbol is odd-pixel border-filled in all cases
                DOM.setStyleAttribute(self.getElement(),
                                "borderWidth",
                                str(floorBW)+"px "+str(floorBW)+"px "+
                                str(ceilBW)+"px " + str(ceilBW)+"px ")

            else:
                DOM.setStyleAttribute(self.getElement(),
                "borderWidth", str(abs(newCappedBorderWidthX2/2))+"px")

            self.cappedBorderWidthX2 = newCappedBorderWidthX2


        if NAI == self.x:
            # At first, use AbsolutePanel's official API
            # (to insulate us from any future AbsolutePanel
            # changes)
            self._parent.setImagePosition(self, newX, newY)
            self.x = newX
            self.y = newY

        else:
            # for speed, just set the edge positions that changed
            # (works, but bypasses AbsolutePanel's official API)
            if self.x != newX:
                DOM.setStyleAttribute(self.getElement(),"left", str(newX)+"px")
                self.x = newX

            if self.y != newY:
                DOM.setStyleAttribute(self.getElement(),"top", str(newY)+"px")
                self.y = newY



        if self.width != newW:
            self.setWidth(str(newW)+ "px")
            self.width = newW

        if self.height != newH:
            self.setHeight(str(newH)+ "px")
            self.height = newH


        if self.backgroundColor != backgroundColor:
            DOM.setStyleAttribute(self.getElement(), "backgroundColor",
                                    backgroundColor)
            self.backgroundColor =backgroundColor

        if self.borderColor != borderColor:
            DOM.setStyleAttribute(self.getElement(), "borderColor", borderColor)
            self.borderColor = borderColor

        if self.borderStyle != borderStyle:
            DOM.setStyleAttribute(self.getElement(), "borderStyle", borderStyle)
            self.borderStyle = borderStyle


        if self.url != url:
            """
            * WARNING: Redundant setUrls cause leaks in FF 2.0.0.16. So, be
            * particularly careful not to accidentally "double set" a URL to
            * the exact same URL (I did this with a slightly less efficient
            * initialization of my images, and this caused a huge memory
            * leak that I hope to memorialize, and lay to rest forever, here.)
            *
            * Symptoms, in FF 2 only, are those that would occur AS IF the
            * extra setUrl increased the reference count on the (browser
            * cached) image file so that Firefox can't release either it, or
            * any of the img elements that reference it. A very big leak for
            * GChart, since just about everything in a GChart references the
            * exact same blank gif URL.
            *
            * Such symptoms did not occur in IE7, or in FF 2 if the cache
            * has been disabled via "about:config".
            *
            * Search for "massively leak" and below that comment you will
            * find two lines that, if uncommented, make the leak reappear.
            *
            """
            self.setUrl(url)
            self.url = url


 # end of class ReusableImage

"""
* A rendering panel contains subpanels
* for Image-element based graphics rendering, canvas-based graphics
* rendering, and Grid-based compass-aligned label rendering.  <p>
*
* Each rendering panel is joined-at-the-hip with, and provides the
* in-the-browser-realization of, a single corresponding GChart curve
* The one exception to this rule are the system curves used
* internally for rendering chart decorations, which, for reasons of
* efficiency, all share the same rendering panel.  <p>
*
* Rather than clearing the widgets contained in the rendering panel
* and recreating and adding them back as needed (which is expensive)
* the rendering panel can make widgets it employs for these purposes
* invisible when not in use and visible again when they are needed
* (which is usually at least twice as fast).  <p>
*
* <p> In principle, this is less memory efficient, but in
* practice, due to the fact that there is less likelyhood of
* fragmentation with reuse than with relying of the garbage
* collector, it could even be more memory efficient.
*
* <p>
*
* When a canvas factory is specified by the developer, the panel
* will include a single canvas widget, where most of the graphical
* elements associated with the curve that uses this rendering panel
* will be drawn.  GChart's canvas support is not yet up to the task
* of rendering everything--it renders only those aspects of the
* chart where canvas rendering provides the biggest quality/speed
* advantages.  So, even if a canvas factory has been provided, many
* aspects of a curve (e.g. the rectangles in bar charts) will still
* be rendered with Image elements.
*
"""

class GraphicsRenderingPanel (AbsolutePanel):
    # Add a canvas, if needed
    def maybeAddCanvas(self):
        canvasFactory = self.chart.getCanvasFactory()
        if None != canvasFactory  and  None == self.canvas:
            self.canvas = canvasFactory.create()
            if None != self.canvas:
                if isinstance(self.canvas, Widget):
                    """
                    * The next line is only needed for IE; it is needed to work-around a
                    * GWTCanvas bug that improperly shifts the x-placement of rendered
                    * graphics when a GChart is placed into a non-left-aligned Grid cell
                    * (GChart uses Grid Widgets to implement its annotations feature, so a
                    * GChart placed as an annotation on another GChart, as would occur with
                    * an inset or popup chart, will end up within an aligned Grid).
                    * <p>
                    *
                    * See also TestGChart46.java, which reproduces the GWTCanvas bug.
                    *
                    """
                    DOM.setElemAttribute(self.canvas.getElement(),
                                        "align", "left")
                    self.canvasPanel.add(self.canvas, 0, 0)

                else:
                    raise IllegalStateException(
                    "Your canvas factory's create method did not return " +
                    "either None or a GWT Widget, as required. See the " +
                    "GChart.setCanvasFactory method javadocs for details.")

    def __init__(self, chart, **kwargs):
        self.chart = chart
        self.canvas = None
        self.x0 = 0;  # origin, in pixel coords, of upper left..
        self.y0 = 0;  #   corner of rendering canvas widget
        self.canvasWidth = 0; # width of last used rendering canvas
        self.canvasHeight = 0; # height of last used rendering canvas
        self.canvasPanel = AbsolutePanel()
        self.imagePanel = PartitionedAbsolutePanel()
        self.imageIndex = 0
        # helps minimize calls to setVisible (which can be expensive)
        self.lastVisibleImage = -1

        AbsolutePanel.__init__(self, **kwargs)
        # Overflow of this panel is controlled when it is added
        #       GChartUtil.setOverflow(this, "visible")
        GChartUtil.setOverflow(self.canvasPanel, "visible")
        GChartUtil.setOverflow(self.imagePanel, "visible")
        # these sub-panels have no size themselves, they are merely
        # there to segregate background, images, and labels.
        self.canvasPanel.setPixelSize(0,0)
        self.imagePanel.setPixelSize(0,0)
        self.add(self.canvasPanel, 0, 0)
        self.add(self.imagePanel, 0, 0)

    def getCanvas(self):
        return self.canvas


    def setImagePosition(self, img, x, y):
        # workaround problem of special meaning of (-1,-1) to
        # setWidgetPosition (makes position off by one pixel, though).
        if x == -1  and  y == -1:
            x = 0

        self.imagePanel.setWidgetPosition(img, x, y)


    # Tells panel you are ready to start drawing the curve on it
    def beginRendering(self, canvasRegion):
        if None != self.canvas:
            if None == canvasRegion:
                # hold onto empty canvas for simplicity
                self.canvas.resize(0, 0)
                self.canvasWidth = self.canvasHeight = 0

            else:
                width = int( round(canvasRegion.width) )
                height = int( round(canvasRegion.height) )
                # if exactly same size, just clear...seems to save a little time
                if width == self.canvasWidth  and  height == self.canvasHeight:
                    self.canvas.clear(); # reuse same canvas

                else:
                    # size changed
                    self.canvas.resize(width, height)
                    self.canvasWidth = width
                    self.canvasHeight = height

                self.x0 = int( round(canvasRegion.x) )
                self.y0 = int( round(canvasRegion.y) )
                # workaround problem with special meaning of (-1,-1) to
                # setWidgetPosition (makes position off by one pixel).
                if self.x0 == -1  and  self.y0 == -1:
                    self.x0 = 0

                self.canvasPanel.setWidgetPosition( self.canvas, self.x0, self.y0)


        self.imageIndex = 0

    # Tells panel you are done drawing on it, and
    # it's OK to do any cleanup/bookkeeping needed.
    def endRendering(self):
        # hide or remove images no longer being used
        if self.chart.optimizeForMemory:
            iImage = (self.imagePanel.getWidgetCount()-1)
        else:
            iImage = self.lastVisibleImage

        while iImage >= self.imageIndex:
            w = self.imagePanel.getWidget(iImage)
            if self.chart.optimizeForMemory:
                self.imagePanel.remove(iImage)
            else:
                DOM.setStyleAttribute(w.getElement(), "visibility", "hidden")
                # setVisible unreliable w Images in IE as shown in TestGChart41a.java
                # w.setVisible(False)
            iImage -= 1

        self.lastVisibleImage = self.imageIndex - 1


    """ Speedier, reusable, rendering-panel-managed images. In effect,
    turns image panel into a specialized memory manager. """
    def addOrRevealImage(self, backgroundColor, borderColor, borderStyle, borderWidth, width, height, x, y, url):
        if self.imageIndex < self.imagePanel.getWidgetCount():
            # reuse an old image
            img = self.imagePanel.getWidget(self.imageIndex)
            if self.imageIndex > self.lastVisibleImage:
                # "" visibility means "visible whenever the parent is visible"
                DOM.setStyleAttribute(img.getElement(), "visibility", "")
                # setVisible unreliable for Images in IE as shown in TestGChart41a.java
                # img.setVisible(True)


        else:
            # add a image
            img = ReusableImage(self)
            self.imagePanel.add(img)


        img.setReusableProperties(backgroundColor,
                                    borderColor,
                                    borderStyle,
                                    borderWidth,
                                    width,
                                    height,
                                    x, y, url)

        if self.lastVisibleImage < self.imageIndex:
            self.lastVisibleImage = self.imageIndex

        self.imageIndex += 1


    def renderBorderedImage(self, backgroundColor, borderColor, borderStyle, borderWidth, width, height, x, y, url):
        """
        if None != canvas  and  url == getBlankImageURL()  and  (borderStyle == USE_CSS  or  borderStyle.equals("solid")):
            # 
            # Use canvas to emulate a transparent, bordered image
            # (GChart can only render solid borders and blank image URLS
            # with canvas at this point)
            #
            #
            drawBorderedImage(backgroundColor,
                                borderColor,
                                borderStyle,
                                borderWidth,
                                width,
                                height,
                                x, y)

        else { # use an actual image HTML element
        """
        self.addOrRevealImage(backgroundColor,
                            borderColor,
                            borderStyle,
                            borderWidth,
                            width,
                            height,
                            x, y, url)

 # end of class GraphicsRenderingPanel

DECORATIVE_RENDERING_PANEL_INDEX = 0

class PlotPanel (AbsolutePanel):
    def __init__(self, chart, **kwargs):

        self.chart = chart

        # keep track of last touched point & hover widget
        self.touchedPoint = None
        self.touchedHoverWidget = None

        # so if user calls update inside hoverUpdate, it won't recurse
        self.insideHoverUpdate = False
        # so if user calls update inside hoverCleanup, it won't recurse
        self.insideHoverCleanup = False

        self.xMax = Double.NaN
        self.xMin = Double.NaN
        self.y2Max = Double.NaN
        self.y2Min = Double.NaN
        self.yMax = Double.NaN
        self.yMin = Double.NaN
        # Retains the last moved-to (Event.ONMOUSEMOVE) client mouse position, or NAI if
        # mouse moved away from chart entirely.
        self.clientX = NAI
        self.clientY = NAI
        # Pixel coords of above mouse position, relative to top-left
        # corner of the GChart (mouse position in GChart's pixel coords)
        self.xMouse = NAI
        self.yMouse = NAI
        # first rendering panel is reserved for chart decorations,
        # and its overflow outside of the plot panel is never hidden
        self.graphicsPanel = AbsolutePanel()
        self.annotationPanel = AbsolutePanel()

        AbsolutePanel.__init__(self, **kwargs)

        # allows labels, symbols, that extend a tad off the
        # chart proper to still appear on the chart; AbsolutePanel
        # default is to truncate these.
        GChartUtil.setOverflow(self, "visible")
        GChartUtil.setOverflow(self.graphicsPanel, "visible")
        GChartUtil.setOverflow(self.annotationPanel, "visible")
        # these sub-panels have no size themselves, they are merely
        # there to segregate the graphical and annotation part of chart
        self.graphicsPanel.setPixelSize(0,0)
        self.annotationPanel.setPixelSize(0,0)
        # this order assures all the annotations are on top of all the graphics
        self.add(self.graphicsPanel, 0, 0)
        self.add(self.annotationPanel, 0, 0)
        # events for hover selection feedback, click event handling
        self.sinkEvents(Event.ONMOUSEMOVE | Event.ONMOUSEOUT |
                        Event.ONCLICK | Event.ONMOUSEOVER)


    """
    * Adds a sub-panel of this plot panel that contains the widgets
    * used to render the graphical parts of the given curve
    * <p>
    *
    * This method must be called just after a curve is added to
    * the chart, to add it's associated graphics rendering panel
    * GChart assumes each curve (except internal decoration rendering
    * curves, which share a single rendering panel for efficiency)
    * already has an corresponding, unique, rendering panel available
    * and ready to go during updates.
    *
    """

    def addGraphicsRenderingPanel(self, rpIndex):
        domInsert = True
        w = GraphicsRenderingPanel(self.chart)
        if (DECORATIVE_RENDERING_PANEL_INDEX == rpIndex  or  
            self.chart.isHoverFeedbackRenderingPanel(rpIndex)  or  
            not self.chart.getClipToPlotArea()):
            # chart decorations and hover feedback are never clipped
            w.setPixelSize(0, 0)
            GChartUtil.setOverflow(w, "visible")

        else:
            w.setPixelSize(self.getXChartSize(), self.getYChartSize())
            GChartUtil.setOverflow(w, "hidden")

        # XXX TODO: investigate what the meaning of domInsert is about
        self.graphicsPanel.insert(w, self.graphicsPanel.getElement(), rpIndex)
        self.graphicsPanel.setWidgetPosition(w, 0, 0)


    """
    * Adds a sub-panel of this plot panel that contains the widgets
    * used to render the annnotations of the given curve
    * <p>
    *
    * This method must be called just after a curve is
    * added to the chart, to add it's associated annotation
    * rendering panel; GChart assumes each curve has a
    * correspondingly indexed rendering panel during updates.
    *
    """

    def addAnnotationRenderingPanel(self, rpIndex):
        domInsert = True
        w = AnnotationRenderingPanel(self.chart)
        # XXX TODO: investigate what the meaning of domInsert is about
        # self.annotationPanel.insert(w, self.annotationPanel.getElement(), rpIndex, domInsert)
        self.annotationPanel.insert(w, self.annotationPanel.getElement(),
                                    rpIndex)
        self.annotationPanel.setWidgetPosition(w, 0, 0)


    """
    * Removes the rendering panel of the curve with the given
    * internal index on the curves list.
    * <p>
    *
    * This method must be called just before a curve is removed
    * from the chart, to remove the widgets used to render
    * that curve in the browser.
    *
    """
    def removeGraphicsRenderingPanel(self, rpIndex):
        self.graphicsPanel.remove(rpIndex)

    def removeAnnotationRenderingPanel(self, rpIndex):
        self.annotationPanel.remove(rpIndex)


    """
    * Returns panel used to render the graphical and textual element of
    * the curve with the given internal index within the browser.
    *
    """
    def getGraphicsRenderingPanel(self, rpIndex):
        if 0 == self.graphicsPanel.getWidgetCount():
            # for lazy addition
            # smaller,faster if all background curves put on single panel
            for i in range(N_PRE_SYSTEM_CURVES-1, len(self.chart.curves)):
                rpInd = self.chart.getRenderingPanelIndex(i)
                self.addGraphicsRenderingPanel(rpInd)

        return self.graphicsPanel.getWidget(rpIndex)

    def getAnnotationRenderingPanel(self, rpIndex):
        if 0 == self.annotationPanel.getWidgetCount():
            # for lazy addition
            # smaller,faster if all background curves put on single panel
            for i in range(N_PRE_SYSTEM_CURVES-1, len(self.chart.curves)):
                rpInd = self.chart.getRenderingPanelIndex(i)
                self.addAnnotationRenderingPanel(rpInd)

        return self.annotationPanel.getWidget(rpIndex)


    def getClientX(self):
        return self.clientX

    def setClientX(self, clientX, isClick):
        """
        * Due to presumed bugs in FF2 and Chrome, space-bar clicking on
        * TestGChart25's "rotate" button produces bogus 0 and/or (in Chrome)
        * seemingly random negative return values from <tt>event.getClient[XY]
        * with the ONCLICK event. IE7 produces correct mouse coordinates for
        * Event.ONCLICK in this case. The bogus coordinates, if not corrected,
        * generate bogus "mouse moved off chart"-like actions (in TestGChart25,
        * Chrome produces inappropriate deselection of the hovered over point
        * after a space-bar invoked update)<p>
        *
        * Workaround is to just ignore any 0 or negative coordinates--thus
        * using the last valid coordinates seen by the chart's mouse tracking
        * code in lieu of the bogus ones.
        *
        * <p>
        *
        * The resulting 1px "partly-dead" band at the top and left edges
        * of the client area due to this workaround (0 is a valid client
        * coordinate) is unlikely to be a significant problem, since
        * clicked-on stuff is rarely clicked on right along the edges
        * of the client area.
        * <p>
        *
        """
        if clientX <= 0  and  isClick:
            return

        elif clientX < 0:
            # some browsers (e.g. FF2) use -1 to indicate undefined mouse coords.
            clientX = NAI


        self.clientX = clientX
        # computing this on-the-fly is VERY expensive, so we retain it
        # (the buffering can be wrong in unusual scrolling scenarios)
        if (NAI == clientX):
            self.xMouse = NAI
        else:
            self.xMouse = (Window.getScrollLeft() + clientX - 
                           self.getAbsoluteLeft())

    def getClientY(self):
        return self.clientY

    # See comments on analogous lines in setClientX above
    def setClientY(self, clientY, isClick):
        if clientY <= 0  and  isClick:
            return

        elif clientY < 0:
            clientY = NAI

        self.clientY = clientY
        if (NAI == clientY):
            self.yMouse = NAI
        else:
            self.yMouse = (Window.getScrollTop() + clientY - 
                           self.getAbsoluteTop())


    """
    * In IE drop-down list boxes, when you enter the dropdown
    * part of the list, client coordinates suddenly become -1, -1
    * (presumably IE's way of saying it won't tell you what they are
    * apparently the dropdown part of the list isn't in the DOM)
    * These repair methods replace such impossible client coordinates
    * with the last valid coordinates.
    * <p>
    *
    * Without this patch, the geometric "within the hover widget"
    * test on GChartExample20a fails in IE7: as soon as user mouses
    * into the dropdown list, the entire hover widget is closed.  <p>
    *
    """
    def repairBadClientX(self, x):
        if x <= 0:
            # 0 isn't strictly bad, but its one of the
            # bad values that can pop up in some browsers.
            return self.clientX

        else:
            return x



    def repairBadClientY(self, y):
        if y <= 0:
            return self.clientY

        else:
            return y



    def getXMouse(self):
        return self.xMouse

    def getYMouse(self):
        return self.yMouse


    # Mouse x position relative to plot area upper left corner.
    def getXMousePlotArea(self):
        result = self.xMouse-self.yAxisEnsembleWidth
        return result

    # Mouse y position relative to plot area upper left corner.
    def getYMousePlotArea(self):
        result = self.yMouse-self.topMargin
        return result


    def getXAxisEnsembleHeight(self):
        return self.xAxisEnsembleHeight

    def getXMax(self):
        return self.xMax

    def getXMin(self):
        return self.xMin

    def getY2AxisEnsembleWidth(self):
        return self.y2AxisEnsembleWidth

    def getY2Max(self):
        return self.y2Max

    def getY2Min(self):
        return self.y2Min

    def getYAxisEnsembleWidth(self):
        return self.yAxisEnsembleWidth


    def legendThickness(self):
        return self.chartLegendThickness

    def chartFootnotesThickness(self):
        return self.chartFootnotesThickness

    def chartTitleThickness(self):
        return self.topMargin


    def getYMax(self):
        return self.yMax

    def getYMin(self):
        return self.yMin


    def reset(self, xChartSize, yChartSize, hasYAxis, hasY2Axis, xAxis, yAxis, y2Axis):

        # these must come first (getTickLabelThickness(False) needs them)
        self.chart.getXAxis().maybePopulateTicks()
        self.chart.getYAxis().maybePopulateTicks()
        self.chart.getY2Axis().maybePopulateTicks()

        self.xChartSize = xChartSize
        self.yChartSize = yChartSize

        axisLimits = xAxis.getAxisLimits()
        self.xMin = axisLimits.min
        self.xMax = axisLimits.max
        axisLimits = yAxis.getAxisLimits()
        self.yMin = axisLimits.min
        self.yMax = axisLimits.max
        axisLimits = y2Axis.getAxisLimits()
        self.y2Min = axisLimits.min
        self.y2Max = axisLimits.max

        self.topMargin = self.chart.getChartTitleThickness()

        self.xAxisEnsembleHeight = (xAxis.getAxisLabelThickness() +
                                xAxis.getTickLabelThickness(False) +
                                xAxis.getTickSpace() +
                                xAxis.getTickLabelPadding())
        self.yAxisEnsembleWidth = (yAxis.getAxisLabelThickness() +
                                yAxis.getTickLabelThickness(False) +
                                yAxis.getTickSpace() +
                                yAxis.getTickLabelPadding())
        self.y2AxisEnsembleWidth = (y2Axis.getAxisLabelThickness() +
                                y2Axis.getTickLabelThickness(False) +
                                y2Axis.getTickSpace() +
                                y2Axis.getTickLabelPadding())

        self.chartLegendThickness = self.chart.getLegendThickness()
        self.chartFootnotesThickness = self.chart.getChartFootnotesThickness()

        self.setPixelSize(self.getXChartSizeDecoratedQuickly(),
                        self.getYChartSizeDecoratedQuickly())

        self.setWidgetPosition(self.graphicsPanel, self.yAxisEnsembleWidth, self.topMargin)
        self.setWidgetPosition(self.annotationPanel, self.yAxisEnsembleWidth, self.topMargin)

        # if there are any existing graphical rendering panels, bring
        # their clipping specs into agreement with the chartspecs
        for i in range(self.getRenderingPanelCount()):
            grp = self.graphicsPanel.getWidget(i)
            if (DECORATIVE_RENDERING_PANEL_INDEX == i  or  
                self.chart.isHoverFeedbackRenderingPanel(i)  or  
                not self.chart.getClipToPlotArea()):
                grp.setPixelSize(0, 0)
                GChartUtil.setOverflow(grp, "visible")

            else:
                grp.setPixelSize(self.getXChartSize(), self.getYChartSize())
                GChartUtil.setOverflow(grp, "hidden")


    def xToChartPixel(self, x):
        result = Double.NaN
        if -Double.MAX_VALUE == x:
            result = self.yAxisEnsembleWidth

        elif Double.MAX_VALUE == x:
            result = self.yAxisEnsembleWidth+self.xChartSize-1.0

        elif not (Double.NaN==(x)):
            result = ((self.yAxisEnsembleWidth * (self.xMax - x) +
                        (self.yAxisEnsembleWidth+self.xChartSize-1.0) * (x - self.xMin))/
                        (self.xMax - self.xMin))

        return result


    def xToPixel(self, x):
        result = Double.NaN
        if -Double.MAX_VALUE == x:
            result = 0

        elif Double.MAX_VALUE == x:
            result = self.xChartSize-1.0

        elif not (Double.NaN==(x)):
            result = (self.xChartSize-1.0) * (x - self.xMin)/(self.xMax - self.xMin)

        return result



    def xChartPixelToX(self, xPx):
        result = Double.NaN
        if NAI != xPx  and  self.xChartSize > 1:
            result = (self.xMin + (self.xMax - self.xMin) *
                        (xPx - self.yAxisEnsembleWidth)/(self.xChartSize-1.))

        return result


    def xPixelToX(self, xPx):
        result = Double.NaN
        if NAI != xPx  and  self.xChartSize > 1:
            result = self.xMin + (self.xMax - self.xMin) * xPx/(self.xChartSize-1.)

        return result



    def dxToPixel(self, dx):
        # xMax and xMin are at centers of their pixels, hence the -1
        result = (dx * (self.xChartSize-1))/(self.xMax-self.xMin)
        return result


    def yToChartPixel(self, y, isY2):
        if isY2:
            minY = self.y2Min 
            maxY = self.y2Max 
        else:
            minY = self.yMin
            maxY = self.yMax
        result = Double.NaN
        if -Double.MAX_VALUE == y:
            result = self.yChartSize + self.topMargin - 1.0

        elif Double.MAX_VALUE == y:
            result = self.topMargin

        elif not (Double.NaN==(y)):
            result = (self.topMargin * (y - minY) +
            ((self.yChartSize + self.topMargin - 1.0) *
            (maxY - y)))/(maxY - minY)

        return result


    def yToPixel(self, y, isY2):
        if isY2:
            minY = self.y2Min 
            maxY = self.y2Max 
        else:
            minY = self.yMin
            maxY = self.yMax
        result = Double.NaN
        if -Double.MAX_VALUE == y:
            result = self.yChartSize - 1.0

        elif Double.MAX_VALUE == y:
            result = 0

        elif not (Double.NaN==(y)):
            result = (self.yChartSize - 1.0) * (maxY - y)/(maxY - minY)

        return result


    def yChartPixelToY(self, yPx):
        result = Double.NaN
        if NAI != yPx  and  self.yChartSize > 1:
            result = self.yMax + (self.yMin - self.yMax) * (yPx - self.topMargin)/(self.yChartSize-1.)

        return result

    def yPixelToY(self, yPx):
        result = Double.NaN
        if NAI != yPx  and  self.yChartSize > 1:
            result = self.yMax + (self.yMin - self.yMax) * yPx/(self.yChartSize-1.)

        return result

    def yChartPixelToY2(self, yPx):
        result = Double.NaN
        if NAI != yPx  and  self.yChartSize > 1:
            result = self.y2Max + (self.y2Min - self.y2Max) * (yPx - self.topMargin)/(self.yChartSize-1.)

        return result

    def yPixelToY2(self, yPx):
        result = Double.NaN
        if NAI != yPx  and  self.yChartSize > 1:
            result = self.y2Max + (self.y2Min - self.y2Max) * yPx/(self.yChartSize-1.)

        return result


    def dyToPixel(self, dy, isY2):
        if isY2:
            minY = self.y2Min 
            maxY = self.y2Max 
        else:
            minY = self.yMin
            maxY = self.yMax
        # maxY and minY are at centers of their pixels, hence the -1
        result = (dy * (self.yChartSize-1))/(maxY-minY)
        return result



    # returns the inner aligned label of the opened hover annotation
    # (this is the one that directly holds the popup hover annotation)
    def getOpenedHoverContainer(self):
        result = None
        c = self.chart.getSystemCurve(HOVER_ANNOTATION_ID)
        if self.touchedPoint is not None  and  c.isVisible():
            internalIndex = self.chart.getInternalCurveIndex(c)
            rpIndex = self.chart.getRenderingPanelIndex(internalIndex)
            arp = self.getAnnotationRenderingPanel(rpIndex)
            result = arp.getFirstInnerAlignedLabel()

        return result


    # the element associated with any opened hover container, else None
    def getOpenedHoverElement(self):
        hoverContainer = self.getOpenedHoverContainer()
        return hoverContainer and hoverContainer.getElement() or None


    """
    * Configures GChart's special selection cursor and
    * hover annotation "system curves" so that they
    * provide appropriate feedback associated with "touching" the
    * given point with the mouse. When rendered, these curves
    * will:
    * <p>
    *
    * <ol>
    * <li> Highlight the selected point in accord with specified hover
    * selection options
    * <p>
    * <li> Display a point-specific hover annotation, in accord with
    * various hover annotation related options.
    *
    * </ol>
    *
    * <p>
    *
    * Also executes <tt>hoverCleanup</tt> on any hover widget
    * associated with the previously touched point, and
    * <tt>hoverUpdate</tt> on any hover widget associated with the
    * newly touched point, and maintains up-to-date references to the
    * last touched point and last touched hover widget.
    *
    """
    def touch(self, p):
        # Note: getTouchedPoint always returns NEW touched point
        prevTouchedPoint = self.touchedPoint
        self.touchedPoint = p
        cAnnotation = self.chart.getSystemCurve(HOVER_ANNOTATION_ID)
        cCursor = self.chart.getSystemCurve(HOVER_CURSOR_ID)
        cTouched = p and p.getParent() or None

        if None != self.touchedHoverWidget:
            # free up resources allocated to previous hover widget
            if not self.insideHoverCleanup:
                try:
                    self.insideHoverCleanup = True
                    self.touchedHoverWidget.hoverCleanup(prevTouchedPoint)

                except:
                    pass
                self.insideHoverCleanup = False




        # with hoverCleanup out of the way, switch to hover widget
        self.touchedHoverWidget = cTouched and \
                                cTouched.getSymbol().getHoverWidget() or None

        if None == self.touchedHoverWidget:
            if None != p:
                # no hover-widget, just use expanded hover-template
                hovertext = p.getHovertext()

                cAnnotation.getPoint(0).setAnnotationText( hovertext,
                    cTouched.getSymbol().getHoverAnnotation().widthUpperBound,
                    cTouched.getSymbol().getHoverAnnotation().heightUpperBound)


        else:
            # touched curve has custom hover widget; update it, etc.
            if not self.insideHoverUpdate:
                try:
                    self.insideHoverUpdate = True
                    self.touchedHoverWidget.hoverUpdate(p)

                except:
                    pass
                self.insideHoverUpdate = False


            cAnnotation.getPoint(0).setAnnotationWidget(
                    self.touchedHoverWidget,
                    cTouched.getSymbol().getHoverAnnotation().widthUpperBound,
                    cTouched.getSymbol().getHoverAnnotation().heightUpperBound)


        if None == p:
            # no longer touching anything
            cAnnotation.setVisible(False)
            cCursor.setVisible(False)

        else:
            # touching something, show that

            if not cTouched.getSymbol().getHoverAnnotationEnabled():
                cAnnotation.setVisible(False)

            else:
                cAnnotation.setVisible(True)
                cAnnotation.setYAxis(cTouched.getYAxis())
                cAnnotation.getPoint(0).setX(p.getX())
                cAnnotation.getPoint(0).setY(p.getY())
                cAnnotation.getSymbol().copy(cTouched.getSymbol())
                # the symbol isn't needed, so make it transparent
                # and zap any images (can't make it 0-sized since
                # annotation placement is size-dependent)
                cAnnotation.getSymbol().setImageURL(
                                DEFAULT_BLANK_IMAGE_URL_FULLPATH)
                cAnnotation.getSymbol().setBackgroundColor("transparent")
                cAnnotation.getSymbol().setBorderColor(TRANSPARENT_BORDER_COLOR)
                if None != cTouched.getSymbol().getHoverAnnotationSymbolType():
                    cAnnotation.getSymbol().setSymbolType(
                        cTouched.getSymbol().getHoverAnnotationSymbolType())

                # else just stick with the touched symbol's type

                # copy the hover annotations specs (including
                # hover widget ref or HTML defined above)
                # to the annotation curve's point
                cAnnotation.getPoint(0).setAnnotationFontColor(
                                cTouched.getSymbol().getHoverFontColor())
                cAnnotation.getPoint(0).setAnnotationFontSize(
                                cTouched.getSymbol().getHoverFontSize())
                cAnnotation.getPoint(0).setAnnotationFontStyle(
                                cTouched.getSymbol().getHoverFontStyle())
                cAnnotation.getPoint(0).setAnnotationFontWeight(
                                cTouched.getSymbol().getHoverFontWeight())
                cAnnotation.getPoint(0).setAnnotationLocation(
                                cTouched.getSymbol().getHoverLocation())
                cAnnotation.getPoint(0).setAnnotationXShift(
                                cTouched.getSymbol().getHoverXShift())
                cAnnotation.getPoint(0).setAnnotationYShift(
                                cTouched.getSymbol().getHoverYShift())


            if not cTouched.getSymbol().getHoverSelectionEnabled():
                cCursor.setVisible(False)

            else:
                cCursor.setVisible(True)
                cCursor.setYAxis(cTouched.getYAxis())
                # place cursor curve's point where touched point is:
                cCursor.getPoint(0).setX(p.getX())
                cCursor.getPoint(0).setY(p.getY())
                # cursor gets (mostly) same props as touched symbol
                cCursor.getSymbol().copy(cTouched.getSymbol())
                if None != cTouched.getSymbol().getHoverSelectionSymbolType():
                    cCursor.getSymbol().setSymbolType(
                    cTouched.getSymbol().getHoverSelectionSymbolType())

                fillSpacing = \
                        cTouched.getSymbol().getHoverSelectionFillSpacing()
                if not (Double.NaN==(fillSpacing)):
                    cCursor.getSymbol().setFillSpacing(fillSpacing)

                fillThickness = \
                        cTouched.getSymbol().getHoverSelectionFillThickness()
                if NAI != fillThickness:
                    cCursor.getSymbol().setFillThickness(fillThickness)

                if NAI != cTouched.getSymbol().getHoverSelectionHeight():
                    cCursor.getSymbol().setHeight(
                            cTouched.getSymbol().getHoverSelectionHeight())

                if NAI != cTouched.getSymbol().getHoverSelectionWidth():
                    cCursor.getSymbol().setWidth(
                            cTouched.getSymbol().getHoverSelectionWidth())

                cCursor.getSymbol().setImageURL(
                        cTouched.getSymbol().getHoverSelectionImageURL())
                cCursor.getSymbol().setBackgroundColor(
                        cTouched.getSymbol().getHoverSelectionBackgroundColor())
                cCursor.getSymbol().setBorderColor(
                        cTouched.getSymbol().getHoverSelectionBorderColor())
                cCursor.getSymbol().setBorderStyle(
                        cTouched.getSymbol().getHoverSelectionBorderStyle())
                borderWidth = \
                        cTouched.getSymbol().getHoverSelectionBorderWidth()
                cCursor.getSymbol().setBorderWidth(borderWidth)




    """
    * Is the given target element contained within the given container?
    * (tried isOrHasChild but was getting exceptions in FF2 I could
    *  not track to their source, so I just stuck with this)
    """
    def isContainedIn(self, container, et):

        if container is None:
            return False
        return DOM.isOrHasChild(et, container)

        # XXX ???? ehh??
        # Element part =
        #(None == et  or  !Element.is(et)) ? None : Element.as(et)
        # TODO: investigate what the above obtuse statement is about
        part = et
        """
        * In Chrome and FF2, the next line makes dropdown lists inside
        * hover widgets work more correctly when they click on the
        * dropdown part of the list. Otherwise, hover widget can close
        * inappropriately. As tested in GChartExample20a.java
        *
        """
        if None == part:
            return True

        try:
            ancestor = part
            while ancestor is not None  and  container is not None:
                if DOM.isSameNode(container, ancestor):
                    return True
                ancestor = ancestor.getParentElement()

        except:
            """
            * In FF2, we get the error "Error: uncaught exception: Permission
            * denied to get property HTMLDivElement.parentNode" if a TextBox is
            * placed into the chart x axis label and you mouse over that textbox
            * (as reported by secnoc in issue #24, which has additional useful info
            * about the likely cause of this problem; TestGChart44.java reproduces
            * this behavior if this try/catch is removed).
            *
            * Returning True, which will act as if the element is contained in the
            * GChart, has "cruft possibilities" as in some cases a hoverwidget may
            * not get closed when user mouses completely out of the GChart, onto a
            * TextBox, but should otherwise be a lesser evil than False or an
            * uncaught exception.
            *
            """
            return True


        return False



    """
    * Is given mouse client point geometrically "inside" container?
    * <p>
    *
    * Note: Certain widgets, like drop-down lists, SuggestBox, etc.
    * implicitly create popups that are not children of the chart, and
    * thus when the user moves into these popups, a mouseout that
    * looks like they are leaving the hover widget or chart, and
    * thus inappropriately hides it can often make hover widgets
    * involving such elements unusable.
    *
    * <p>
    *
    * But, by adding a geometric condition to define "being out of
    * the chart or hover widget", hover widgets that use such popups
    * can avoid such inappropriate hiding as long as the popups remain
    * geometrically within either the chart as a whole, or the hover
    * widget itself.  For example a form with drop-down lists is OK
    * as long as the drop down lists don't extrude off the form
    * when they drop down.<p>
    *
    * Unfortunately, this creates another problem, in that hover
    * widgets that extrude off the chart can remain open when the user
    * mouses off the chart in such a way that the mouseout occurs at a
    * point geometrically within the hover widget. We consider this
    * small amount of "hover cruft" a lesser evil than not being able
    * to use dropdown lists and such within hover widgets at all.
    * <p>
    *
    * Often a more natural solution, rather than wrestling with such
    * "geometrical popup containment", is a click-invoked modal
    * dialog. But that has a distinctly different feel than the more
    * nearly modeless hover widget, so I thought there was room/need
    * for both approaches.
    *
    """
    def isGeometricallyContainedIn(self, container, clientX, clientY):

        if None == container:
            raise IllegalArgumentException( "Container cannot be None")

        result = False


        """
        * Equations below shrink container 1px around its perimeter,
        * to account for apparent roundoff errors in FF2 associated
        * with window scrolling. FF2 mouseout events get dropped
        * (about half the time, with random scroll position choices
        * hence my roundoff suspicions--problem did not occur in
        * Chrome or IE7) without this 1px shrinkage. End users can't
        * discriminate a 1px mouse shift anyway, so there is no
        * real downside (except that you had to read this comment)
        * to using this workaround.
        *
        """
        y = Window.getScrollTop() + self.repairBadClientY(clientY)
        absTop = DOM.getAbsoluteTop(container)
        if absTop < y  and  y+1 < absTop + DOM.getOffsetHeight(container):
            x = Window.getScrollLeft() + self.repairBadClientX(clientX)
            absLeft = DOM.getAbsoluteLeft(container)
            if absLeft < x  and  x+1 < absLeft + DOM.getOffsetWidth(container):
                result = True



        return result


    # Touches the underlying object at the last event's mouse
    # position if it is different from the currently touched point,
    # or if retouch is True. Returns True if a touch occured.
    def touchObjectAtMousePosition(self, retouch=False):
        result = False
        pointAtPosition = self.chart.getClosestBrushTouchingPointNoCheck(
                            self.getXMousePlotArea(), self.getYMousePlotArea())
        if (pointAtPosition != self.touchedPoint)  or  retouch:
            self.touch(pointAtPosition)
            result = True

        return result

    # touch object at mouse, even if it is the same one as last time
    def retouchObjectAtMousePosition(self):
        self.touchObjectAtMousePosition(True)


    """
    * Does the event occur over the currently opened hover
    * annotation?
    *
    * This method helps us to ignore mouse clicks and moves over a
    * "sticky-open" hover annotation, or one of its children. Idea
    * is to prevent the hover feedback from jumping to another
    * point while the user interacts with an opened hover widget.
    * <p>
    *
    * This is not just important for hover annotations that contain
    * buttons and such, but even for hover annotations based on
    * text, since the user might want to select/copy that
    * text (involving mouse moves) for example.
    *
    *
    """
    def isOverOpenedHoverAnnotation(self, event):
        result = False
        hoverElement = self.getOpenedHoverElement()
        if None != hoverElement:
            if self.isContainedIn(hoverElement, DOM.eventGetTarget(event)):
                result = True

            elif self.isGeometricallyContainedIn(hoverElement,
                                             DOM.eventGetClientX(event), 
                                              DOM.eventGetClientY(event)):
                result = True


        return result


    """
    * Does event (assumed a MOUSEOUT) take the mouse completely
    * outside of the current chart?
    * <p>
    *
    * To be completely outside the chart, the event must be both not
    * associated with any child element of the chart (as represented
    * in the DOM) and geometrically outside of the chart's "box" and
    * the "box" of any currently opened hover annotation.  <p>
    *
    * Because a GChart is rendered with many DOM elements, moving
    * the mouse across it generates many MOUSEOUT events. This
    * method lets us focus on only those that take us completely off
    * the chart, and thus require the hover feedback to be turned
    * off.
    * <p>
    *
    *
    *
    """
    def takesUsCompletelyOutsideChart(self, event):
        result = True

        if self.isContainedIn(self.getElement(), DOM.eventGetToElement(event)):
            """ hoverElement is always a descendant of the main chart element due to
            * how GChart generates it, so if this branch isn't reached, toElement
            * is not contained in either chart or the opened hover annotation """
            result = False

        elif self.isGeometricallyContainedIn(self.getElement(),
                                             DOM.eventGetClientX(event), 
                                              DOM.eventGetClientY(event)):
            result = False

        else:
            hoverElement = self.getOpenedHoverElement()
            if None != hoverElement:
                if self.isGeometricallyContainedIn(hoverElement,
                                                 DOM.eventGetClientX(event),
                                                 DOM.eventGetClientY(event)):
                    result = False




        return result




    """*
    * Fired whenever a browser event is recieved.
    * <p>
    *
    * GChart keeps track of browser mouse-moves, mouse-outs,
    * mouse-overs, and mouse clicks and will automatically provide
    * appropriate hover feedback whenever the mouse "touches"
    * rendered symbols on the chart. It also maintains a reference
    * to the "currently touched" point which you can retrieve via
    * the <tt>getTouchedPoint</tt> method.  <p>
    *
    * GChart never "eats" mouse events (it just watches them go by,
    * and keeps track of what the mouse-anchored brush is touching)
    * so containing Widgets can track and respond to the same mouse
    * event stream after GChart does, if they want to.
    *
    * <p>
    *
    * Each curve's symbol can configure how hover feedback is
    * displayed via the <tt>setHover*</tt> family of methods and the
    * related HoverUpdateable and HoverParameterInterpreter
    * interfaces. In addition, GChart implements the standard
    * GWT <tt>SourcesClickEvents</tt> interface, so you
    * can easily implement <tt>ClickListener.onClick</tt>
    * to be notified of user clicks on a GChart, using
    * <tt>getTouchedPoint</tt> to grab the clicked-on point.
    * <p>
    *
    * This method can only properly track events when
    * <tt>isUpdateNeeded</tt> returns False (implies DOM/GChart
    * specs are in synch) so if you want this tracking system to
    * work as intended, you need to be sure to always call
    * <tt>update</tt> after making a series of chart specification
    * changes, just before you give control back to the browser.
    *
    *
    * @param event the browser event that GChart will monitor
    * so as to maintain a reference to the "touched" point and
    * provide appropriate hover feedback.
    *
    * @see #touch touch
    * @see #getTouchedPoint getTouchedPoint
    * @see #setHoverWidget setHoverWidget
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverAnnotationEnabled setHoverAnnotationEnabled
    * @see #setHoverSelectionEnabled setHoverSelectionEnabled
    * @see HoverUpdateable HoverUpdateable
    * @see #setHoverParameterInterpreter setHoverParameterInterpreter
    * @see HoverParameterInterpreter HoverParameterInterpreter
    * @see #isUpdateNeeded isUpdateNeeded
    * @see #update update
    *
    """
    def onBrowserEvent(self, event):
        # GWT docs say without this, 1.6+ event handlers won't work
        AbsolutePanel.onBrowserEvent(self, event)

        """
        * The tracking of the mouse position depends on if there are
        * opened hover annotations or not (mouse moves over such
        * annotations don't get tracked, and thus don't change the
        * "touched" point). However, all of that dependency can be
        * determined by the current DOM rendering of the chart--there
        * is no need to look at actual chart specs.  <p>
        *
        * So, when the DOM/chart specs are inconsistent (chart "needs
        * update") we continue to perform mouse tracking based on the
        * <i>last completed DOM rendering</i> of the chart (that is,
        * the last <tt>assembleChart</tt> call).  However, actual
        * changes to the chart are "frozen" (as assured by the
        * <tt>!isUpdateNeeded</tt> test below) so no DOM changes
        * occur automatically in response to mouse moves over things
        * (e.g. no changes to hover feedback occur--that's frozen,
        * too). In short, we track, but do not act.
        *
        * <p>
        *
        * We can think of it this way: mouse tracking remains
        * consistent with the <i>last DOM rendered</i> specification
        * and then it is as if all of the accumulated specification
        * changes are applied to the DOM at that point in time when
        * the next (developer invoked) update occurs. That means
        * there is exactly one point in time of "unpredictable
        * change" (points previously hovered over can disappear from
        * under the mouse since they have been deleted or moved,
        * etc.). But that discontinuity can be adequately managed by
        * the developer via the <tt>TouchedPointUpdateOption</tt>
        * argument to update.
        * <p>
        *
        * Well, that's the theory. But GChart's mouse tracking has
        * only been tested for the case where <tt>update</tt> is
        * always called just before the developer cedes control back
        * to the browser after making a series of chart spec changes.
        * So, the docs warn developers to be sure that they do
        * that, too. But the hope is that specialized applications
        * where they don't call update until the user explicitly asks
        * for that (say, for a very busy chart with an editing
        * capability and a "refresh" button) will also work OK.
        *
        * <p>
        *
        * Another important consequence of this "track but don't act"
        * approach is that it assures that only cheap/quick
        * operations can be triggered automatically by direct user
        * mousing. Potentially expensive "full chart" updates always
        * require a direct developer update invocation. So, if the
        * system "locks up while it's doing a lengthly update" there
        * will always be an actual developer line of code responsible
        * for that, not some mysteriously event-triggered call.
        *
        *
        """

        eventId = DOM.eventGetType(event)
        """ Note that a click that closes a modal DialogBox can
        * generate a mouse location change without an ONMOUSEMOVE,
        * and a point that moves under the mouse due to an update
        * can generate a mouseover without a MOUSEMOVE """
        isClick = ("click" == eventId)
        if ("mousemove" == eventId  or  "mouseover" == eventId  or  isClick)  and  not self.isOverOpenedHoverAnnotation(event):
            # remember last "tracked" mouse location
            """
            if "click" == eventId:
                log.writebr("CLICK: event.getClientX()=" + str(DOM.eventGetClientX(event)) +
                " event.getClientY()=" + str(DOM.eventGetClientY(event)) +
                " event.getTarget()==self.getElement() is " +
                str(DOM.eventGetTarget(event) == self.getElement()) +
                " event.getCurrentTarget()="+str(DOM.eventGetCurrentTarget(event)) +
                " event.getTarget()=" + str(DOM.eventGetTarget(event)))

            elif "mouseover" == eventId:
                log.writebr("MOUSEOVER: event.getClientX()=" + str(DOM.eventGetClientX(event)) +
                " event.getClientY()=" + str(DOM.eventGetClientY(event)) +
                " event.getCurrentTarget()="+str(DOM.eventGetCurrentTarget(event)) +
                " event.getTarget()=" + str(DOM.eventGetTarget(event)))

            """
            if self.chart.getHoverTouchingEnabled()  or  isClick:
                self.setClientX(DOM.eventGetClientX(event), isClick)
                self.setClientY(DOM.eventGetClientY(event), isClick)
                if (not self.chart.isUpdateNeeded()  and  
                    self.touchObjectAtMousePosition(isClick)):
                    self.chart.assembleChart()



        elif "mouseout" == eventId  and  self.chart.getHoverTouchingEnabled()  and  self.takesUsCompletelyOutsideChart(event):
            """
            log.writebr("MOUSEOUT: event.getClientX()=" + str(DOM.eventGetClientX(event)) +
                " event.getClientY()=" + str(DOM.eventGetClientY(event)) +
                " event.getCurrentTarget()="+str(DOM.eventGetCurrentTarget(event)) +
                " event.getTarget()=" + str(DOM.eventGetTarget(event)))
            """
            self.setClientX(NAI, False); # mouse not over chart,
            self.setClientY(NAI, False); # so position is undefined
            if (not self.chart.isUpdateNeeded()  and  
                self.touchObjectAtMousePosition()):
                self.chart.assembleChart()







    # Is chart's DOM rendering consistent with its specs?
    def isValidated(self):
        result = True
        i = 0
        while result  and  i < len(self.chart.curves):
            result = self.chart.curves[i].isValidated()
            i += 1
        return result


    """
    * Returns number of "rendering panels" that there actually
    * are right now.
    *
    * GChart's implementation assures that this number is exactly the
    * same for the graphics and annotation rendering panels.
    *
    """
    def getRenderingPanelCount(self):
        result = self.graphicsPanel.getWidgetCount()
        return result

    def getXChartSize(self):
        return self.xChartSize


    def getYChartSize(self):
        return self.yChartSize

    # quickly returns decorated xChartsize as of the last plotPanel.reset
    def getXChartSizeDecoratedQuickly(self):
        result = (self.xChartSize +
                    self.yAxisEnsembleWidth +
                    self.y2AxisEnsembleWidth +
                    self.chartLegendThickness)
        return result


    # quickly returns decorated yChartsize as of the last plotPanel.reset
    def getYChartSizeDecoratedQuickly(self):
        result = (self.yChartSize +
                    self.xAxisEnsembleHeight +
                    self.topMargin +
                    self.chartFootnotesThickness)
        return result



 # end of class PlotPanel



