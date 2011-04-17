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

import time

from pyjamas.ui.HTML import HTML

from pyjamas.chart import NumberFormat
from pyjamas.chart import DateTimeFormat
from pyjamas.chart import Double
from pyjamas.chart import TickLocation
from pyjamas.chart import AnnotationLocation
from pyjamas.chart import Annotation

from pyjamas.chart.GChartConsts import NAI
from pyjamas.chart.GChartConsts import DEFAULT_TICK_COUNT
from pyjamas.chart.GChartConsts import DEFAULT_WIDGET_WIDTH_UPPERBOUND 
from pyjamas.chart.GChartConsts import DEFAULT_WIDGET_HEIGHT_UPPERBOUND
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LABEL_FONT_COLOR
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LABEL_FONTSIZE
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LABEL_FONT_STYLE
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LABEL_FONT_WEIGHT
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LABEL_FORMAT
from pyjamas.chart.GChartConsts import DEFAULT_TICK_LENGTH
from pyjamas.chart.GChartConsts import DEFAULT_TICK_THICKNESS
from pyjamas.chart.GChartConsts import Y2TICKS_ID
from pyjamas.chart.GChartConsts import Y2GRIDLINES_ID
from pyjamas.chart.GChartConsts import Y2AXIS_ID
from pyjamas.chart.GChartConsts import YTICKS_ID
from pyjamas.chart.GChartConsts import YGRIDLINES_ID
from pyjamas.chart.GChartConsts import YAXIS_ID
from pyjamas.chart.GChartConsts import XTICKS_ID
from pyjamas.chart.GChartConsts import XGRIDLINES_ID
from pyjamas.chart.GChartConsts import XAXIS_ID
from pyjamas.chart.GChartConsts import TICK_CHARHEIGHT_TO_FONTSIZE_LOWERBOUND 
from pyjamas.chart.GChartConsts import TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND 
from pyjamas.chart.GChartConsts import Y_AXIS
from pyjamas.chart.GChartConsts import Y2_AXIS

from pyjamas.chart.GChartUtil import htmlHeight, htmlWidth

# these are used in formatting tick positions into tick labels:
NUMBER_FORMAT_TYPE = 0
DATE_FORMAT_TYPE = 1
LOG10INVERSE_FORMAT_TYPE = 2
LOG2INVERSE_FORMAT_TYPE = 3


"""*
** Represents an axis of the chart, for example, the x,
** y, or y2 axis. An axis consists of the axis itself,
** along with its tick marks, tick labels and gridlines.
**
** @see XAxis XAxis
** @see YAxis YAxis
** @see Y2Axis Y2Axis
** @see #getXAxis getXAxis
** @see #getYAxis getYAxis
** @see #getY2Axis getY2Axis
**
**
*"""
class AxisLimits:
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def equals(self, al):
        return (al.min == min  and  al.max == max)

class Axis:
    def __init__(self, chart):
        self.chart = chart
        self.tickLocation = TickLocation.DEFAULT_TICK_LOCATION
        self.numberFormat = NumberFormat.getFormat(DEFAULT_TICK_LABEL_FORMAT)
        self.dateFormat = DateTimeFormat.getShortDateTimeFormat()
        self.tickLabelFormatType = NUMBER_FORMAT_TYPE
        self.nCurvesVisibleOnAxis = 0;  # # of developer curves on axis.
        # (count does not include system or
        # invisible curves)

        # different initial curr, prev ==> "limits have changed" state
        self.currentLimits = AxisLimits( Double.MAX_VALUE, -Double.MAX_VALUE)
        self.previousLimits = AxisLimits( -Double.MAX_VALUE, Double.MAX_VALUE)

        self.axisLabel = None
        self.axisLabelThickness = NAI
        self.hasGridlines = False
        self.tickCount = DEFAULT_TICK_COUNT
        # axes auto-scale whenever min or max are NaN.
        self.axisMax = Double.NaN
        self.axisMin = Double.NaN
        # this symbol facilitates rendering of gridlines & axes
        self.tickLabelFontColor = DEFAULT_TICK_LABEL_FONT_COLOR
        # In CSS font-size pixels. These define the height of each
        # character; our code relies on the rule of thumb that
        # character width is approximately 3/5th this height to
        # obtain a reasonably tight upper bound on tick label widths.
        self.tickLabelFontSize = DEFAULT_TICK_LABEL_FONTSIZE
        self.tickLabelFontStyle = DEFAULT_TICK_LABEL_FONT_STYLE
        self.tickLabelFontWeight = DEFAULT_TICK_LABEL_FONT_WEIGHT

        self.tickLabelFormat = DEFAULT_TICK_LABEL_FORMAT
        self.tickLabelThickness = NAI
        self.tickLabelPadding = 0
        self.ticksPerLabel = 1
        self.ticksPerGridline = 1
        self.tickLength = DEFAULT_TICK_LENGTH

        # this symbol facilitates rendering of labeled tick-marks
        self.tickThickness = DEFAULT_TICK_THICKNESS

        # is axis itself visible (has no impact ticks or their labels)
        self.axisVisible = True

    def getChart(self):
        return self.chart

    def getSystemCurve(self, idx):
        return self.chart.getSystemCurve(idx)

    def incrementCurves(self):
        self.nCurvesVisibleOnAxis += 1

    def decrementCurves(self):
        self.nCurvesVisibleOnAxis -= 1

    # adds a labeled tick mark via this Axis' special system tick curve
    def addTickAsPoint(self, tickPosition, tickLabel, tickWidget, widthUpperBound, heightUpperBound):

        c = self.getSystemCurve(self.ticksId)
        if self.isHorizontalAxis:
            c.addPoint(tickPosition, self.axisPosition*Double.MAX_VALUE)

        else:
            c.addPoint(self.axisPosition*Double.MAX_VALUE, tickPosition)


        # unlabeled tick--we are done, so return to save time
        if None == tickLabel  and  None == tickWidget:
            return

        #add an annotation representing the tick label
        p = c.getPoint()
        if self.isHorizontalAxis:
            # below tick on X, above it on (the future) X2
            p.setAnnotationLocation( (self.axisPosition < 0) and AnnotationLocation.SOUTH or AnnotationLocation.NORTH)
            if self.tickLabelPadding != 0:
                # padding < 0 is rare but allowed
                p.setAnnotationYShift(self.axisPosition*tickLabelPadding)
                # else stick with default of 0 y-shift


        else:
            # to left of tick mark on Y, to right of it on Y2
            p.setAnnotationLocation( (self.axisPosition < 0) and AnnotationLocation.WEST or AnnotationLocation.EAST)
            if self.tickLabelPadding != 0:
                p.setAnnotationXShift(self.axisPosition*self.tickLabelPadding)

            # else stick with default of 0 x-shift



        if None != tickLabel:
            p.setAnnotationText(tickLabel, widthUpperBound, heightUpperBound)

        elif None != tickWidget:
            p.setAnnotationWidget(tickWidget, widthUpperBound, heightUpperBound)


        p.setAnnotationFontSize(self.getTickLabelFontSize())
        p.setAnnotationFontStyle(self.getTickLabelFontStyle())
        p.setAnnotationFontColor(self.getTickLabelFontColor())
        p.setAnnotationFontWeight(self.getTickLabelFontWeight())


    """*
    * Adds a tick at the specified position with the specified
    * label on this axis, whose width and height are within
    * the specified upper-bounds.
    *
    * <p>
    * Note that explicitly adding a single tick via this method
    * will eliminate any auto-generated ticks associated with the
    * <tt>setTickCount</tt> method.
    *
    * <p>
    * Use this method to specify unusually spaced
    * tick marks with labels that do not directly
    * reflect the position (for example, for a logarithmic axis,
    * or for a bar chart with special keyword-type labels, or
    * a time axis that places date and time on two separate lines).
    *
    * @param tickPosition the position, in model units, along
    *   this axis at which the tick is displayed.
    *   For example, if the axis range goes from 0 to 1,
    *   a tick at position 0.5 would appear in the middle of
    *   the axis.
    *
    *  @param tickLabel the label for this tick.  HTML is
    *  supported in tick labels, but it must be prefixed by
    *  <tt>&lt;html&gt</tt>.  See the {@link
    *  Curve.Point#setAnnotationText(String,int,int)
    *  setAnnotationText} method for more information.
    *
    *  @param widthUpperBound an upper bound on the width of
    *  the text or HTML, in pixels. Use <tt>NAI</tt> to
    *  get GChart to estimate this width for you. See the
    *  <tt>setAnnotationText</tt> method for more information.
    *
    *  @param heightUpperBound an upper bound on the height of
    *  the text or HTML, in pixels. Use <tt>NAI</tt> to
    *  get GChart to estimate this height for you. See the
    *  <tt>setAnnotationText</tt> method for more information.
    *
    * @see #clearTicks clearTicks
    * @see #addTick(double) addTick(double)
    * @see #addTick(double,String) addTick(double,String)
    * @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    * @see #setTickCount setTickCount
    * @see #setTickLabelFormat setTickLabelFormat
    * @see #setTickLabelFontSize setTickLabelFontSize
    * @see #setTickLabelFontStyle setTickLabelFontStyle
    * @see #setTickLabelFontColor setTickLabelFontColor
    * @see #setTickLabelFontWeight setTickLabelFontWeight
    * @see Curve.Point#setAnnotationText(String,int,int)
    *      setAnnotationText
    * @see Curve.Point#setAnnotationWidget setAnnotationWidget
    *
    """
    def _addTickLabel(self, tickPosition, tickLabel, widthUpperBound, heightUpperBound):
        self.chartDecorationsChanged = True
        if NAI != self.tickCount:
            # clear out any auto-generated ticks
            cTicks = self.getSystemCurve(self.ticksId)
            cTicks.clearPoints()
            self.tickCount = NAI

        self.addTickAsPoint(tickPosition, tickLabel, None, widthUpperBound,
                        heightUpperBound)

    def addTick(self, tickPosition, tickWidget=None,
                                    widthUpperBound=None,
                                    heightUpperBound=None):
        """*
        *  Adds a widget-defined tick label at the specified
        *  position, whose width and height are within
        *  the specified upper-bounds.
        *
        * @param tickPosition the position, in model units, along
        *   this axis at which the tick is displayed.
        *   For example, if the axis range goes from 0 to 1,
        *   a tick at position 0.5 would appear in the middle of
        *   the axis.
        *
        *  @param tickWidget the label for this tick, as defined
        *  by any GWT Widget.
        *
        *  @param widthUpperBound an upper bound on the width of
        *  the widget, in pixels. If this and the next
        *  parameter are omitted, GChart will use
        *  <tt>DEFAULT_WIDGET_WIDTH_UPPERBOUND</tt>.
        *
        *  @param heightUpperBound an upper bound on the height of
        *  the widget, in pixels. If this and the previous
        *  parameter are omitted, GChart will use <tt>
        *  DEFAULT_WIDGET_HEIGHT_UPPERBOUND</tt>
        *
        *  @see #addTick(double,Widget) addTick(double,Widget)
        *  @see #addTick(double,String,int,int) addTick(double,String,int,int)
        *  @see Curve.Point#setAnnotationWidget setAnnotationWidget
        *  @see #DEFAULT_WIDGET_WIDTH_UPPERBOUND DEFAULT_WIDGET_WIDTH_UPPERBOUND
        *  @see #DEFAULT_WIDGET_HEIGHT_UPPERBOUND DEFAULT_WIDGET_HEIGHT_UPPERBOUND
        *"""

        if tickWidget is None:
            tiickWidget = self.formatAsTickLabel(tickPosition)

        if isinstance(tickWidget, str):
            if widthUpperBound is None and heightUpperBound is None:
                widthUpperBound = NAI
                heightUpperBound = NAI
            self._addTickLabel(tickPosition, tickWidget,
                               widthUpperBound, heightUpperBound)
            return

        if widthUpperBound is None and heightUpperBound is None:
            widthUpperBound = DEFAULT_WIDGET_WIDTH_UPPERBOUND
            heightUpperBound = DEFAULT_WIDGET_HEIGHT_UPPERBOUND
        self.chartDecorationsChanged = True
        if NAI != self.tickCount:
            # clear out any auto-generated ticks
            cTicks = self.getSystemCurve(self.ticksId)
            cTicks.clearPoints()
            self.tickCount = NAI

        self.addTickAsPoint(tickPosition, None, tickWidget, widthUpperBound,
                            heightUpperBound)



    def clearTicks(self):
        """*
        *
        * Removes all ticks from this axis. Specifically,
        * erases any ticks that were explicitly specified via
        * <tt>addTick</tt>, and also sets the tick count to 0.
        * <p>
        *
        * @see #setTickCount setTickCount
        * @see #addTick(double) addTick(double)
        * @see #addTick(double,String) addTick(double,String)
        * @see #addTick(double,String,int,int) addTick(double,String,int,int)
        * @see #addTick(double,Widget) addTick(double,Widget)
        * @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
        *
        """
        self.chartDecorationsChanged = True
        self.tickCount = NAI
        c = self.getSystemCurve(self.ticksId)
        c.clearPoints()



    def clientToModel(self, clientCoordinate):
        """*
        * Converts a pixel, client-window coordinate position along this
        * axis into the model units associated with this axis.
        *
        * @param clientCoordinate a pixel-based coordinate that defines
        * the dimension associated with this axis in the standard
        * client window coordinates of GWT.
        *
        * @return the location defined by the client-coordinate argument,
        * but converted into the model units associated
        * with this axis.
        *
        * @see #getMouseCoordinate getMouseCoordinate
        * @see #modelToClient modelToClient
        * @see #pixelToModel pixelToModel
        * @see #modelToPixel modelToPixel
        *
        *
        """
        pass

    def formatAsTickLabel(self, value):
        """*
        *
        * Applies this axis' tick label format to format a given value.
        *
        * @return the value formated as per this axis' currently specified
        * tick label format.
        *
        * @see  #setTickLabelFormat(String) setTickLabelFormat
        *
        """
        result = None
        if self.tickLabelFormatType == DATE_FORMAT_TYPE:
            #Date transDate = Date((long) value)
            transDate = time.gmtime(value)
            result = self.dateFormat.format(transDate)

        elif self.tickLabelFormatType == LOG10INVERSE_FORMAT_TYPE:
            value = pow(10., value)
            result = self.numberFormat.format(value)

        elif self.tickLabelFormatType == LOG2INVERSE_FORMAT_TYPE:
            value = pow(2., value)
            result = self.numberFormat.format(value)

        else:
            result = self.numberFormat.format(value)

        return result

    def formatNumberAsTickLabel(self, value):
        """*
        * @deprecated
        *
        * Equivalent to the better-named formatAsTickLabel.

        * <p>
        *
        * @see #formatAsTickLabel formatAsTickLabel
        *
        """
        return self.formatAsTickLabel(value)


    def getAxisLabel(self):
        """* Returns the previously specified label of this axis.
        **
        ** @return the Widget used as the label of this axis
        **
        ** @see #setAxisLabel setAxisLabel
        **
        """
        return self.axisLabel


    def getAxisLabelThickness(self):
        """* Returns the thickness of the axis-label-holding region
        ** adjacent to the region allocated for this axis' tick labels.
        ** <p>
        **
        ** Note that if the axis label is <tt>None</tt> (the
        ** default) then this method always returns 0, since
        ** in that case no rectangular region will be allocated
        ** for the axis label.
        ** <p>
        **
        ** @return the thickness of the axis-label-holding
        ** region, in pixels.
        **
        ** @see #setAxisLabelThickness setAxisLabelThickness
        **
        """
        result = 0
        # Base class implementation is for y axes (x-axis will override).
        EXTRA_CHARWIDTH = 2; # 1-char padding on each side
        DEF_CHARWIDTH = 1; # when widget has no text
        if None == self.getAxisLabel():
            result = 0

        elif NAI != self.axisLabelThickness:
            result = self.axisLabelThickness

        elif hasattr(self.getAxisLabel(), 'getHTML'):
            charWidth = htmlWidth( self.getAxisLabel().getHTML())
            result = int ( round((charWidth + EXTRA_CHARWIDTH) *
                            self.getTickLabelFontSize() *
                            TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND))

        elif hasattr(self.getAxisLabel(), "getText"):
            text = self.getAxisLabel().getText()
            result = int (round((EXTRA_CHARWIDTH +
                            (text and len(text) or 0)) *
                            self.getTickLabelFontSize() *
                            TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND))

        else:
            # non-text widget. Not a clue, just use def width
            result = int ( round(
                            (DEF_CHARWIDTH + EXTRA_CHARWIDTH) *
                            self.getTickLabelFontSize() *
                            TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND) )

        return result

    def getAxisMax(self):
        """*
        ** Returns the maximum value displayed on this axis.
        ** If the explicitly specified maximum value is
        ** undefined (<tt>Double.NaN</tt>) the maximum value returned
        ** by this function is calculated as the maximum of
        ** all of the values either displayed on this axis via
        ** points on a curve, or explicitly specified via tick
        ** positions.
        **
        ** @return maximum value visible on this axis, in
        ** "model units" (arbitrary, application-specific,
        ** units)
        **
        ** @see #setAxisMax setAxisMax
        ** @see #getDataMin getDataMin
        ** @see #getDataMax getDataMax
        *"""

        if not (Double.NaN==(self.axisMax)):
            return self.axisMax

        elif NAI != self.tickCount:
            return self.getDataMax()

        else:
            return max(self.getDataMax(), self.getTickMax())


    def getAxisMin(self):
        """*
        **
        ** Returns the minimum value displayed on this axis.
        ** If the minimum value is undefined (<tt>Double.NaN</tt>) the
        ** minimum value returned by this function is the
        ** minimum of all of the values either displayed on
        ** this axis via points on a curve, or explicitly specified
        ** via tick positions.
        **
        ** @return minimum value visible on this axis, in
        ** "model units" (arbitrary, application-specific,
        ** units)
        **
        ** @see #setAxisMin setAxisMin
        *"""
        if not (Double.NaN==(self.axisMin)):
            return self.axisMin; # explicitly set

        elif NAI != self.tickCount:
            return self.getDataMin()

        else:
            return min(self.getDataMin(), self.getTickMin())



    def getAxisVisible(self):
        """* Is axis line visible on the chart? Note that
        ** this property only determines the visibility of the axis line
        ** itself. It does not control the visibility of the
        ** tick marks or tick labels along this axis.
        ** <p>
        **
        ** @return True if the axis line is visible, False otherwise.
        **
        ** @see #setAxisVisible setAxisVisible
        **
        *"""
        return self.axisVisible




    def getDataMax(self):
        """* Returns the maximum data value associated with values
        ** represented on this axis. For example, for the left
        ** y-axis, this would be the largest y-value of all points
        ** contained in curves that are displayed on the left y-axis.
        **
        ** @return the maximum value associated with values
        **   mapped onto this axis.
        **
        ** @see #getDataMin getDataMin
        ** @see #getAxisMax getAxisMax
        ** @see #getAxisMin getAxisMin
        **
        """
        pass

    def getDataMin(self):
        """* Returns the minimum data value associated with values
        ** represented on this axis. For example, for the left
        ** y-axis, this would be the smallest y-value of all points
        ** contained in curves that are displayed on the left y-axis.
        **
        ** @return the minimum value associated with values
        **   mapped onto this axis.
        **
        ** @see #getDataMax getDataMax
        ** @see #getAxisMax getAxisMax
        ** @see #getAxisMin getAxisMax
        **
        """
        pass

    def getHasGridlines(self):
        """* Returns the gridline setting previously made with
        ** <tt>setHasGridlines</tt>.
        **
        ** @return True if gridlines have been enabled, False if not.
        **
        ** @see #setHasGridlines setHasGridlines
        **
        *"""
        return hasGridlines


    def getMouseCoordinate(self):
        """*
        * Returns the coordinate along this axis that
        * is associated with the last "GChart-tracked" mouse
        * location.
        *
        * @return the coordinate, projected along this axis, in
        *   the scale defined by this axis, representing the
        *   position GChart has currently "tracked" the mouse to,
        *   or <tt>Double.NaN</tt> if GChart has tracked the mouse
        *   right off the edge of the chart.
        *
        * @see #clientToModel clientToModel
        * @see #modelToClient modelToClient
        * @see #pixelToModel pixelToModel
        * @see #modelToPixel modelToPixel
        * @see GChart#setHoverTouchingEnabled setHoverTouchingEnabled
        *
        """
        pass
    def getNCurvesVisibleOnAxis(self):
        """*
        * Returns the number of visible curves displayed on this axis.
        * <p>
        *
        * @return the number of visible curves on this axis, or <tt>0</tt> if
        * there are no visible curves on this axis.
        *
        * @see Axis#setVisible setVisible
        *
        """
        return self.nCurvesVisibleOnAxis

    def getTickCount(self):
        """*
        ** Returns the number of ticks on this axis.
        **
        ** @return the number of ticks on this axis.
        **
        ** @see #setTickCount setTickCount
        ** @see #addTick(double) addTick(double)
        ** @see #addTick(double,String) addTick(double,String)
        ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
        ** @see #addTick(double,Widget) addTick(double,Widget)
        ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
        ** @see #clearTicks clearTicks
        **
        *"""
        result = self.tickCount
        if NAI == self.tickCount:
            c = self.getSystemCurve(self.ticksId)
            result = c.getNPoints()

        return result


    def getTickLabelFontWeight(self):
        """*
        ** Returns the CSS font-weight specification to be used
        ** by this axis' tick labels.
        **
        ** @return font-weight of this axis' tick labels
        **
        ** @see #setTickLabelFontWeight setTickLabelFontWeight
        *"""
        return self.tickLabelFontWeight

    def getTickLabelFontColor(self):
        """*
        ** Returns the color of the font used to display the
        **    text of the tick labels on this axis.
        **
        **
        ** @return CSS color string defining the color of the text of
        **    the tick labels for this axis.
        **
        ** @see #setTickLabelFontColor setTickLabelFontColor
        **
        ** @see #DEFAULT_TICK_LABEL_FONT_COLOR DEFAULT_TICK_LABEL_FONT_COLOR
        **
        **
        **
        *"""
        return self.tickLabelFontColor


    def getTickLabelFontStyle(self):
        """*
        ** Returns the font-style of the font used to render tick
        ** labels on this axis (typically either "italic" or
        ** "normal")
        **
        ** @return the CSS font-style in which tick labels of this axis
        **   are rendered.
        **
        ** @see #setTickLabelFontStyle setTickLabelFontStyle
        *"""
        return self.tickLabelFontStyle

    def getTickLabelFontSize(self):
        """* Returns the CSS font size, in pixels, used for tick labels
        ** on this axis.
        **
        ** @return the tick label font size in pixels
        **
        ** @see #setTickLabelFontSize setTickLabelFontSize
        *"""
        return self.tickLabelFontSize


    def getTickLabelFormat(self):
        """*
        ** Returns the tick label numeric format string for this
        ** axis.
        **
        ** @return numeric format used to generate tick labels.
        **
        ** @see #setTickLabelFormat setTickLabelFormat
        **
        *"""
        return self.tickLabelFormat

    def getTickLabelPadding(self):
        """*
        ** Returns the amount of padding (blank space) between the
        ** ticks and their labels.<p>
        **
        ** @return amount of padding between ticks and their labels,
        ** in pixels.
        **
        ** @see #setTickLabelPadding setTickLabelPadding
        **
        *"""
        return self.tickLabelPadding

    # Does real work of getTickLabelThickness; flag saves time
    # during repeated calls made in updateChartDecorations.
    def getTickLabelThickness(self, needsPopulation=True):
        maxLength = 0
        if self.tickLabelThickness != NAI:
            result = self.tickLabelThickness
        else:
            # use an heuristic to estimate thickness
            if needsPopulation:
                self.maybePopulateTicks()

            c = self.getSystemCurve(self.ticksId)
            nTicks = c.getNPoints()
            for i in range(nTicks):
                tt = c.getPoint(i).getAnnotationText()
                if None != tt:
                    maxLength = max(maxLength,
                            Annotation.getNumberOfCharsWide(tt))


            result = int (round(maxLength * self.tickLabelFontSize *
                                TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND))

        return result


    def getTicksPerGridline(self):
        """*
        ** Returns the ratio of the number of ticks to the number of
        ** ticks that have an associated gridline.
        **
        ** @return number of ticks per gridline for this axis
        **
        ** @see #setTicksPerGridline setTicksPerGridline
        **
        *"""
        return self.ticksPerGridline

    def getTicksPerLabel(self):
        """*
        ** Returns the ratio of the number of ticks to the number of
        ** labeled ticks.
        **
        ** @return number of ticks per label.
        **
        ** @see #setTicksPerLabel setTicksPerLabel
        **
        *"""
        return self.ticksPerLabel


    def getTickLength(self):
        """*
        * Returns the length of ticks for this axis.
        *
        * @return the length of this axis' ticks, in pixels.
        *
        * @see #setTickLength setTickLength
        """
        return self.tickLength


    # GChart adds a pixel to even, centered, tick lengths (only
    # odd-length HTML ticks can be exactly centered on 1px axis)
    def getActualTickLength(self):
        result = self.tickLength
        if (TickLocation.CENTERED == self.tickLocation  and
            0 == (self.tickLength % 2)  and  self.tickLength > 0):
            result += 1

        return result


    def getTickLocation(self):
        """*
        * Returns relative location of ticks on this axis.
        * <p>
        *
        * @see #setTickLocation setTickLocation
        *
        * @return <tt>TickLocation.INSIDE</tt>,
        *         <tt>TickLocation.OUTSIDE</tt>, or
        *         <tt>TickLocation.CENTERED</tt>
        *
        """
        return self.tickLocation



    def getTickSpace(self):
        """* Returns the amount of space along the axis reserved for
        *  the tick marks themselves, in pixels.
        *  <p>
        *
        *  This equals the length of
        *  the part of the tick that is outside of the plot area.
        *
        * @see #setTickLength setTickLength
        * @see #setTickLabelPadding setTickLabelPadding
        * @see #setTickLocation setTickLocation
        *
        * @return the space GChart will allocate just outside the
        * axis to hold any tick marks.
        *
        """

        if TickLocation.CENTERED == self.tickLocation:
            result = (self.tickLength+1)/2;  # round up to nearest pixel

        elif TickLocation.OUTSIDE == self.tickLocation:
            result = self.tickLength

        else: # INSIDE
            result = 0

        return result



    def getTickThickness(self):
        """*
        * Returns the thickness of ticks for this axis.
        *
        * @return the thickness of this axis' ticks, in pixels.
        *
        * @see #setTickThickness setTickThickness
        * @see #getTickLength getTickLength
        """
        return tickThickness


    def modelToClient(self, modelCoordinate):
        """*
        * Converts a coordinate position in the model units associated
        * with this axis into a corresponding coordinate position
        * expressed in standard GWT client-window pixel coordinates.

        * @param modelCoordinate the position along this axis defined
        *  in the model units associated with this axis.
        *
        * @return a pixel-based coordinate that defines
        * the position associated with the argument in the standard
        * pixel, client window, coordinates of GWT.
        *
        * @see #getMouseCoordinate getMouseCoordinate
        * @see #clientToModel clientToModel
        * @see #pixelToModel pixelToModel
        * @see #modelToPixel modelToPixel
        *
        *
        """
        pass

    def modelToPixel(self, modelCoordinate):
        """*
        * Converts a coordinate position in the model units associated
        * with this axis into a corresponding coordinate position
        * expressed in GChart's decorated chart pixel coordinates.

        * @param modelCoordinate a position on this axis expressed
        *  in the model units associated with this axis.
        *
        * @return the distance,
        * in pixels, from the left edge (for the x axis) or top
        * edge (for the y or y2 axis) of
        * the decorated chart to the given position on this axis.
        *
        * @see #getMouseCoordinate getMouseCoordinate
        * @see #clientToModel clientToModel
        * @see #modelToClient modelToClient
        * @see #modelToPlotAreaPixel modelToClient
        * @see #pixelToModel pixelToModel
        *
        """
        pass


    """*
    * Converts a coordinate position in the model units associated
    * with this axis into a corresponding coordinate position
    * expressed in GChart's plot area pixel coordinates.
    * <p>
    *
    * These
    * coordinates have their origin at the upper left corner
    * of the plot area, and x pixel-coordinates that increase
    * as you move right, and y pixel-coordinates that increase
    * as you move down.
    * <p>
    *
    * The plot area is the rectangular region bounded by the
    * chart's axes, and with a size specified via
    * <tt>setChartSize</tt>, where the chart's curves are
    * typically displayed.
    * <p>
    *
    * Apart from a shift in the origin of the pixel coordinates
    * used, this method works just like <tt>modelToPixel</tt>
    * see that method for additional details, tips, and
    * restrictions.
    *
    * @param modelCoordinate a position on this axis expressed
    *  in the model units associated with this axis.
    *
    * @return the distance,
    * in pixels, from the left edge (for the x axis) or top
    * edge (for the y or y2 axis) of
    * the plot area to the given position on this axis.
    *
    * @see #getMouseCoordinate getMouseCoordinate
    * @see #plotAreaPixelToModel plotAreaPixelToModel
    * @see #modelToPixel modelToPixel
    * @see #setChartSize setChartSize
    *
    """
    def modelToPlotAreaPixel(self, modelCoordinate):
        pass


    """*
    * Converts a coordinate position in GChart's decorated
    * chart pixel
    * coordinates into the model units associated with this axis.
    * <p>
    *
    * GChart's decorated chart pixel
    * coordinates have their origin at the upper left corner
    * of the decorated GChart, and x pixel-coordinates that increase
    * as you move right, and y pixel-coordinates that increase
    * as you move down. They are related to GWT's standard
    * client window coordinates via the following equations:
    *
    * <pre>
    *   xClient = plotPanel.getAbsoluteLeft()
    *             - Window.getScrollLeft()
    *             + xPixel
    *   yClient = plotPanel.getAbsoluteTop()
    *             - Window.getScrollTop()
    *             + yPixel
    * </pre>
    * <p>
    *
    *
    * In the above <tt>plotPanel</tt> is an internal
    * <tt>AbsolutePanel</tt>
    * GChart creates to hold the entire, decorated, chart. Apart from
    * borders and such applied to the GChart as a whole, its
    * absolute top and left positions should be the same as
    * those of the GChart itself.
    * <p>
    *
    * For example, for a completely undecorated chart (no tick labels,
    * legend keys, etc.) the plot area takes up the entire chart. In
    * that case, if the pixel units of the plot area range from
    * <tt>0...100</tt> along this axis, and the model coordinates range
    * from <tt>0...10</tt> along this axis, then
    * <tt>pixelToModel(pixelCoordinate)</tt> returns
    * <tt>pixelCoordinate/10.</tt>.  <p>
    *
    * The model/pixel mapping is as of the last <tt>update</tt>
    * this method returns <tt>Double.NaN</tt> before the first
    * <tt>update</tt>. Note that, unlike <tt>clientToModel</tt>
    * and <tt>modelToClient</tt>, the GChart does <i>not</i>
    * need to be actually rendered within the browser for you to
    * use this method.
    * <p>
    *
    * <i>Tip:</i> If you need to access this mapping before
    * the first real update, you can explicitly specify the min and
    * max of this axis via <tt>setAxisMin</tt> and
    * <tt>setAxisMax</tt>, and then call <tt>update</tt> before adding
    * any curves to the chart (which, since the chart is empty, should
    * be very fast). This approach will allow you to convert between
    * model and pixel coordinates before the first real update, and
    * before the chart is rendered in the browser.
    * <p>
    *
    * @param pixelCoordinate the distance,
    * in pixels, from the left edge (for the x axis) or top
    * edge (for the y or y2 axis) of
    * the decorated chart to a point on this axis.
    *
    * @return that same position on this axis expressed in the
    *  the model units associated with this axis.
    *
    * @see #getMouseCoordinate getMouseCoordinate
    * @see #clientToModel clientToModel
    * @see #modelToClient modelToClient
    * @see #modelToPixel modelToPixel
    * @see #plotAreaPixelToModel plotAreaPixelToModel
    *
    """
    def pixelToModel(self, pixelCoordinate):
        pass


    """*
    * Converts a coordinate position in GChart's plot area
    * pixel
    * coordinates into the model units associated with this axis.
    * <p>
    *
    * GChart's plot area pixel
    * coordinates have their origin at the upper left corner
    * of the plot area, and x pixel-coordinates that increase
    * as you move right, and y pixel-coordinates that increase
    * as you move down.
    * <p>
    *
    * The plot area is the rectangular region bounded by the
    * chart's axes, and with a size specified via
    * <tt>setChartSize</tt>, where the chart's curves are
    * typically displayed.
    * <p>
    *
    * Apart from a shift in the origin of the pixel coordinates
    * used, this method works just like <tt>pixelToModel</tt>
    * see that method for additional details, tips, and
    * restrictions.
    *
    * @param pixelCoordinate the distance,
    * in pixels, from the left edge (for the x axis) or top
    * edge (for the y or y2 axis) of
    * the plot area to a point on this axis.
    *
    * @return that same position on this axis expressed in the
    *  the model units associated with this axis.
    *
    * @see #modelToPlotAreaPixel modelToPlotAreaPixel
    * @see #pixelToModel pixelToModel
    * @see #setChartSize setChartSize
    *
    """
    def plotAreaPixelToModel(self, pixelCoordinate):
        pass




    """* Specifies the label of this axis.
    ** <p>
    **
    ** This label will be positioned just outside of, and
    ** centered lengthwise on, the region adjacent to
    ** this axis that GChart reserves for this axis' tick labels.
    **
    ** @param axisLabel a Widget to use as the label of this axis.
    **
    ** @see #getAxisLabel getAxisLabel
    ** @see #setTickLabelThickness setTickLabelThickness
    ** @see #setAxisLabelThickness setAxisLabelThickness
    **
    """

    def setAxisLabel(self, axisLabel):
        if isinstance(axisLabel, str):
            axisLabel = HTML(axisLabel)
        self.axisLabel = axisLabel
        self.chartDecorationsChanged = True


    """* Sets the thickness of the axis-label-holding region
    ** adjacent to the region allocated for tick labels.<p>
    **
    ** The axis label widget will be centered in this region.
    ** Choose a thickness large enough to hold the largest
    ** font size you want users to be able to zoom up to
    ** without the axis label spilling over into
    ** adjacent regions.
    ** <p>
    **
    ** If the axis label thickness is <tt>NAI</tt> (the
    ** default), and the widget defining the axis label
    ** implements <tt>HasHTML</tt> (or <tt>HasText</tt>) then
    ** GChart uses a thickness based on the estimated number of
    ** non-tag characters in the first <tt>&lt;br&gt;</tt> or
    ** <tt>&lt;li&gt;</tt>
    ** delimited line for y-axis labels, and based on the
    ** estimated number of (<tt>&lt;br&gt;</tt> or
    ** <tt>&lt;li&gt;</tt> delimited)
    ** text lines for x-axis labels.<p>
    **
    ** Note that if the axis label is <tt>None</tt> (its
    ** default setting) then no space is allocated for the axis
    ** label, regardless of this thickness setting.
    ** <p>
    **
    ** @param thickness the thickness of the axis-label-holding
    ** region, in pixels, or <tt>NAI</tt> to use
    ** GChart's character-based default thickness estimates.
    **
    ** @see #getAxisLabelThickness getAxisLabelThickness
    ** @see #setAxisLabel setAxisLabel
    """
    def setAxisLabelThickness(self, thickness):
        axisLabelThickness = thickness
        self.chartDecorationsChanged = True


    """*
    ** Specifies the maximum value visible on this axis.
    ** <p>
    **
    ** Aspects of the chart rendered beyond this maximum will
    ** be clipped if the chart's <tt>clipToPlotArea</tt>
    ** property is <tt>True</tt>.
    **
    ** <p>
    **
    ** If <tt>Double.NaN</tt> is specified, this maximum
    ** is auto-determined as described in <tt>getAxisMax</tt>.
    **
    ** <p> <i>Performance tip:</i> Using auto-determined axis
    ** limits (via <tt>Double.NaN</tt>) forces GChart, at the
    ** next update, to re-render many chart elements whenever
    ** the min or max data value displayed on this axis
    ** changes.  These (often expensive) re-renderings can be
    ** avoided by using explicitly specified axis limits
    ** whenever possible. <p>
    **
    ** @param max maximum value visible on this axis, in "model units"
    ** (arbitrary, application-specific, units) or <tt>Double.NaN</tt>
    ** (the default value) to use an auto-determined maximum.
    **
    ** @see #getAxisMax getAxisMax
    ** @see #getDataMin getDataMin
    ** @see #getDataMax getDataMax
    ** @see GChart#setClipToPlotArea setClipToPlotArea
    **
    *"""
    def setAxisMax(self, max):
        self.chartDecorationsChanged = True
        self.axisMax = max

    """*
    ** Specifies the minimum value of this axis.
    ** <p>
    **
    ** Aspects of the chart rendered at positions before this
    ** minimum
    ** value will be clipped if the chart's
    ** <tt>clipToPlotArea</tt> property is <tt>True</tt>.
    ** <p>
    **
    ** If <tt>Double.NaN</tt> is specified, this minimum
    ** is auto-determined as described in <tt>getAxisMin</tt>.
    **
    ** <p> <i>Performance tip:</i> Using auto-determined axis
    ** limits (via <tt>Double.NaN</tt>) forces GChart, at the
    ** next update, to re-render many chart elements whenever
    ** the min or max data value displayed on this axis
    ** changes.  These (often expensive) re-renderings can be
    ** avoided by using explicitly specified axis limits
    ** whenever possible. <p>
    **
    ** @param min minimum value visible on this axis, in "model units"
    ** (arbitrary, application-specific, units), or Double.NaN
    ** (the default) to use an auto-determined minimum.
    **
    ** @see #getAxisMin getAxisMin
    ** @see #getDataMin getDataMin
    ** @see #getDataMax getDataMax
    **
    *"""
    def setAxisMin(self, min):
        # min can change axis label width ==> changes position of plot area
        self.chartDecorationsChanged = True
        self.axisMin = min


    """*
    ** Defines if this axis is visible. Note that
    ** this property only defines the visibility of the axis line
    ** itself, it does not control the visibility of
    ** tick marks or tick labels associated with the axis.
    **
    ** <p>
    ** <i>Tip:</i>Tick marks can be made invisible by using
    ** <tt>setTickThickness</tt> to set the tick thickness
    ** to 0. Tick labels can be made invisible by using
    ** <tt>setTickLabelFontColor</tt> to set the tick label
    ** color to the chart's background color.
    ** <p>
    **
    ** @param axisVisible False to hide axis, True to show it.
    **
    ** @see #setTickThickness setTickThickness
    ** @see #setTickLabelFontColor setTickLabelFontColor
    ** @see #getAxisVisible getAxisVisible
    *"""
    def setAxisVisible(self, axisVisible):
        self.chartDecorationsChanged = True
        self.axisVisible = axisVisible


    """*
    ** Specifies if this axis should have gridlines. When an
    ** axis has gridlines, tick marks with indexes <tt>0, N,
    ** 2*N,...</tt> where <tt>N</tt> is the value of this axis'
    ** <tt>ticksPerGridline</tt> property, are in effect
    ** extended across the entire chart.
    **
    ** @param hasGridlines True to display gridlines,
    ** False (the default) to not display them.
    **
    ** @see #getHasGridlines getHasGridlines
    ** @see #setTicksPerGridline setTicksPerGridline
    **
    *"""
    def setHasGridlines(self, hasGridlines):
        self.chartDecorationsChanged = True
        self.hasGridlines = hasGridlines

    """* Sets the number of ticks to be placed on this axis. The
    ** default tick count is 10. Ticks are always evenly
    ** spaced across the entire axis, unless explicitly
    ** specified via <tt>addTick</tt>.
    ** <p>
    **
    ** Note that setting the tick count overrides (erases)
    ** any ticks explicitly specified via <tt>addTick</tt>.
    **
    ** @param tickCount the number of ticks for this axis.
    **
    ** @see #getTickCount getTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double, String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    ** @see #setTickLabelFormat setTickLabelFormat
    ** @see #setTickLabelFontSize setTickLabelFontSize
    ** @see #setTickLabelFontStyle setTickLabelFontStyle
    ** @see #setTickLabelFontColor setTickLabelFontColor
    ** @see #setTickLabelFontWeight setTickLabelFontWeight
    **
    *"""
    def setTickCount(self, tickCount):
        self.chartDecorationsChanged = True
        self.getSystemCurve(self.ticksId).clearPoints(); # eliminate user specified ticks
        self.tickCount = tickCount

    """*
    ** Specifies the weight of the font used in this axis' tick
    ** labels.
    **
    ** @param cssWeight the weight of the font, such as bold,
    **    normal, light, 100, 200, ... 900, for tick labels.
    **
    ** @see #getTickLabelFontWeight getTickLabelFontWeight
    ** @see #setTickLabelFormat setTickLabelFormat
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    ** @see #setTickLabelFontStyle setTickLabelFontStyle
    ** @see #setTickLabelFontColor setTickLabelFontColor
    ** @see #setTickLabelFontSize setTickLabelFontSize
    ** @see #DEFAULT_TICK_LABEL_FONT_WEIGHT DEFAULT_TICK_LABEL_FONT_WEIGHT
    *"""
    def setTickLabelFontWeight(self, cssWeight):
        self.chartDecorationsChanged = True
        # assure that any existing ticks are updated with weight
        c = self.getSystemCurve(self.ticksId)
        nPoints = c.getNPoints()
        for i in range(nPoints):
            c.getPoint(i).setAnnotationFontWeight(cssWeight)
        self.tickLabelFontWeight = cssWeight

    """*
    ** Specifies the color of the font used to render tick labels
    ** for this axis.
    **
    ** <p>
    ** For more information on standard CSS color
    ** specifications see the discussion in
    ** {@link Symbol#setBackgroundColor Symbol.setBackgroundColor}.
    ** <p>
    **
    ** @param cssColor color of the font used to display this
    **    axis' tick labels, in standard CSS format.
    **
    ** @see #getTickLabelFontColor getTickLabelFontColor
    ** @see #setTickLabelFormat setTickLabelFormat
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    ** @see #setTickLabelFontStyle setTickLabelFontStyle
    ** @see #setTickLabelFontWeight setTickLabelFontWeight
    ** @see #setTickLabelFontSize setTickLabelFontSize
    *"""
    def setTickLabelFontColor(self, cssColor):
        self.chartDecorationsChanged = True
        c = self.getSystemCurve(self.ticksId)
        nPoints = c.getNPoints()
        for i in range(nPoints):
            c.getPoint(i).setAnnotationFontColor(cssColor)
        self.tickLabelFontColor = cssColor


    """*
    ** Specifies the CSS font-style of this
    ** axis' tick labels.
    **
    ** @param cssStyle any valid CSS font-style, namely,
    **   normal, italic, oblique, or inherit.
    **
    ** @see #getTickLabelFontStyle getTickLabelFontStyle
    ** @see #setTickLabelFormat setTickLabelFormat
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    ** @see #setTickLabelFontColor setTickLabelFontColor
    ** @see #setTickLabelFontWeight setTickLabelFontWeight
    ** @see #setTickLabelFontSize setTickLabelFontSize
    ** @see #DEFAULT_TICK_LABEL_FONT_STYLE
    ** DEFAULT_TICK_LABEL_FONT_STYLE
    *"""
    def setTickLabelFontStyle(self, cssStyle):
        self.chartDecorationsChanged = True
        c = self.getSystemCurve(self.ticksId)
        nPoints = c.getNPoints()
        for i in range(nPoints):
            c.getPoint(i).setAnnotationFontStyle(cssStyle)
        self.tickLabelFontStyle = cssStyle


    """*
    ** Sets the CSS font size for tick labels on this
    ** axis, in pixels.
    **
    ** @param tickLabelFontSize the font size of tick labels
    **   displayed on this axis.
    **
    ** @see #getTickLabelFontSize getTickLabelFontSize
    ** @see #setTickLabelFormat setTickLabelFormat
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    ** @see #setTickLabelFontStyle setTickLabelFontStyle
    ** @see #setTickLabelFontColor setTickLabelFontColor
    ** @see #setTickLabelFontWeight setTickLabelFontWeight
    ** @see GChart#DEFAULT_TICK_LABEL_FONTSIZE DEFAULT_TICK_LABEL_FONTSIZE
    **
    *"""

    def setTickLabelFontSize(self, tickLabelFontSize):
        self.chartDecorationsChanged = True
        c = self.getSystemCurve(self.ticksId)
        nPoints = c.getNPoints()
        for i in range(nPoints):
            c.getPoint(i).setAnnotationFontSize(tickLabelFontSize)
        self.tickLabelFontSize = tickLabelFontSize


    """*
    * Specifies a format string to be used in
    * converting the numeric values associated with each
    * tick on this axis into tick labels.  This string must
    * follow the conventions of the number format patterns
    * used by the GWT <a
    * href="http:#google-web-toolkit.googlecode.com/svn/javadoc/1.4/com/google/gwt/i18n/client/NumberFormat.html">
    * NumberFormat</a> class, <i>with three
    * exceptions:</i>
    * <p>
    * <ol>
    *
    *  <li><i>Log10 inverse prefix</i>: If the string begins
    *  with the prefix <tt>=10^</tt> the value is replaced with
    *  <tt>pow(10.,value)</tt> and the so-transformed value is
    *  then formatted using the part of the format string that
    *  comes after this prefix, which must be a valid GWT
    *  <tt>NumberFormat</tt> pattern (e.g. "##.##").
    *  <p>
    *  For an example of how to use this prefix to create a
    *  semi-log plot, see <a
    *  href="package-summary.html#GChartExample04">the
    *  Chart Gallery's GChartExample04</a>.
    *  <p>
    *
    *  <li><i>Log2 inverse prefix</i>: If the string begins with
    *  the prefix <tt>=2^</tt> the value is replaced with
    *  <tt>pow(2.,value)</tt> and the so-transformed value is
    *  then formatted using the part of the format string that
    *  comes after this prefix, which must be a valid GWT
    *  <tt>NumberFormat</tt> pattern.
    *  <p>
    *
    *  <li><i>Date casting prefix</i>: If the string begins with
    *  the prefix <tt>=(Date)</tt> the value is replaced with
    *  <tt>Date((long) value)</tt> and the so-transformed
    *  value is then formatted using the format string that
    *  comes after this prefix, which must be a valid GWT
    *  <a href="http:#google-web-toolkit.googlecode.com/svn/javadoc/1.4/com/google/gwt/i18n/client/DateTimeFormat.html">
    *  DateTimeFormat</a>  pattern (e.g. "yyyy-MM-dd&nbsp;HH:mm").
    *  For the special case format string of <tt>"=(Date)"</tt>
    *  (just the date casting prefix) GChart uses the
    *  <tt>DateTimeFormat</tt> returned by the
    *  <tt>DateTimeFormat.getShortDateTimeFormat</tt> method.  <p>
    *
    *  Note that the values associated with this Axis must
    *  represent the number of milliseconds since January 1,
    *  1970 (in the GMT time zone) whenever this date
    *  casting prefix is used.  <p>
    *
    *
    *  For example, if the x-axis tick label format were
    *  "=(Date)MMM-dd-yyyy HH", then, for a tick located at the
    *  x position of 0, the tick label would be "Jan-01-1970 00"
    *  (on a client in the GMT time zone) and for a tick located
    *  at the x position of 25*60*60*1000 (one day + one hour,
    *  in milliseconds) the tick label would be "Jan-02-1970 01"
    *  (again, on a GMT-based client). Results would be
    *  shifted appropriately on clients in different time zones.
    *  <p>
    *
    *  Note that if your chart is based on absolute, GMT-based,
    *  millisecond times then date labels will change when your
    *  chart is displayed on clients in different time zones.
    *  Sometimes, this is what you want. To keep the date labels
    *  the same in all time zones, convert date labels into Java
    *  <tt>Date</tt> objects in your client-side code, then use
    *  the <tt>Date.getTime</tt> method, also in your
    *  client-side code, to convert those dates into the
    *  millisecond values GChart requires.  The <a
    *  href="package-summary.html#GChartExample12"> Chart
    *  Gallery's GChartExample12</a> illustrates how to use this
    *  second approach to produce a time series chart whose
    *  date-time labels are the same in all time zones.
    *
    *  <p>
    *
    *  <blockquote><small>
    *
    *  Ben Martin describes an alter(and more flexible)
    *  approach to formatting time series tick labels in his <a
    *  href="http:#www.linux.com/feature/132854">GChart
    *  tutorial</a>. Ben's article, along with Malcolm Gorman's
    *  related <a
    *  href="http:#groups.google.com/group/Google-Web-Toolkit/msg/6125ce39fd2339ac">
    *  GWT forum post</a> were the origin of this date
    *  casting prefix. Thanks! </small></blockquote>
    *
    * </ol>
    * <p>
    *
    *
    * <p> Though HTML text is not supported in the tick label
    * format string, you can change the size, weight, style, and
    * color of tick label text via the
    * <tt>setTickLabelFont*</tt> family of methods. You
    * <i>can</i> use HTML in tick labels (e.g. for a multi-line
    * x-axis label) but but only if you define each tick label
    * explicitly using the <tt>addTick</tt> method.
    *
    * @param format an appropriately prefixed
    *   GWT <tt>NumberFormat</tt> compatible or
    *   GWT <tt>DateTimeFormat</tt> compatible format string that
    *   defines how to convert tick values into tick labels.
    *
    * @see #setTickCount setTickCount
    * @see #addTick(double) addTick(double)
    * @see #addTick(double,String) addTick(double,String)
    * @see #addTick(double,String,int,int) addTick(double,String,int,int)
    * @see #addTick(double,Widget) addTick(double,Widget)
    * @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    * @see #setTickLabelFontSize setTickLabelFontSize
    * @see #setTickLabelFontStyle setTickLabelFontStyle
    * @see #setTickLabelFontColor setTickLabelFontColor
    * @see #setTickLabelFontWeight setTickLabelFontWeight
    * @see #getTickLabelFormat getTickLabelFormat
    """
    def setTickLabelFormat(self, format):
        # interpret prefixes and create an appropriate formatter
        if self.tickLabelFormat == format:
            return

        self.chartDecorationsChanged = True
        if format.startswith("=(Date)"):
            transFormat = format[len("=(Date)"):]
            if transFormat.equals(""):
                # so "=(Date)" works
                self.dateFormat = DateTimeFormat.getShortDateTimeFormat()

            else: # e.g. "=(Date)mm/dd/yy hh:mm"
                self.dateFormat = DateTimeFormat.getFormat(transFormat)

            self.tickLabelFormatType = DATE_FORMAT_TYPE

        elif format.startswith("=10^"):
            transFormat = format[len("=10^"):]
            self.numberFormat = NumberFormat.getFormat(transFormat)
            self.tickLabelFormatType = LOG10INVERSE_FORMAT_TYPE

        elif format.startswith("=2^"):
            transFormat = format[len("=2^"):]
            self.numberFormat = NumberFormat.getFormat(transFormat)
            self.tickLabelFormatType = LOG2INVERSE_FORMAT_TYPE

        else:
            self.numberFormat = NumberFormat.getFormat(format)
            self.tickLabelFormatType = NUMBER_FORMAT_TYPE

        # remember original format (for use with the getter)
        self.tickLabelFormat = format


    """* Specifies the number of pixels of padding (blank space)
    ** between the tick marks and their labels. <p>
    **
    ** With the default of <tt>0</tt>, each
    ** tick label is flush against its tick mark.
    **
    ** @param tickLabelPadding the amount of padding between
    ** tick labels and tick marks, in pixels.
    **
    **
    ** @see #getTickLabelPadding getTickLabelPadding
    ** @see #setTickLength setTickLength
    ** @see #setTickLocation setTickLocation
    **
    *"""
    def setTickLabelPadding(self, tickLabelPadding):
        self.chartDecorationsChanged = True
        self.tickLabelPadding = tickLabelPadding

    """* Specifies the thickness of the region adjacent to
    ** this axis that GChart will reserve for purposes of
    ** holding this axis' tick labels.  <p>
    ** <p>
    **
    ** For vertical axes, this represents the width of the
    ** widest tick label, for horizontal axes, this represents
    ** the height of highest tick label.
    ** <p>
    **
    **
    ** By default, this property has the special "undefined"
    ** value <tt>NAI</tt>. With this value, the
    ** companion method <tt>getTickLabelThickness</tt> uses an
    ** HTML-based heuristic to estimate the thickness.
    **
    **
    ** @see #getTickLabelThickness getTickLabelThickness
    ** @see #setTickLabelFontSize setTickLabelFontSize
    ** @see #setTickLocation setTickLocation
    ** @see #setTickLabelPadding setTickLabelPadding
    ** @see #setAxisLabel setAxisLabel
    ** @see NAI NAI
    **
    *"""
    def setTickLabelThickness(self, tickLabelThickness):
        self.chartDecorationsChanged = True
        self.tickLabelThickness = tickLabelThickness

    """* Specifies the ratio of the number of tick marks on the
    ** axis, to the number of gridlines on the axis.
    ** <p>
    **
    ** For example, with the default value of 1, every tick has
    ** an associated gridline, whereas with a
    ** <tt>ticksPerGridline</tt> setting of 2, only the first,
    ** third, fifth, etc. ticks have gridlines.
    **
    ** <p>
    **
    ** This setting only has an impact when the axis' gridlines
    ** are turned on, that is, when this axis'
    ** <tt>getHasGridlines</tt> method returns True.
    **
    ** @see #setHasGridlines setHasGridlines
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    **
    ** @param ticksPerGridline the number of ticks on this
    **   axis per "gridline-extended" tick.
    **
    *"""
    def setTicksPerGridline(self, ticksPerGridline):
        if ticksPerGridline <= 0:
            raise IllegalArgumentException("ticksPerGridline=" +
            ticksPerGridline + "; ticksPerGridline must be > 0")

        self.chartDecorationsChanged = True
        self.ticksPerGridline = ticksPerGridline

    """* Specifies the ratio of the number of tick marks on the
    ** axis, to the number of labeled tick marks on the axis.
    ** <p>
    **
    ** For example, with the default value of 1, every tick is
    ** labeled, whereas with a <tt>ticksPerLabel</tt> setting
    ** of 2, only the first, third, fifth, etc. ticks are
    ** labeled.
    **
    ** <p>
    **
    ** This setting is only used when tick labels
    ** are specified implicitly via <tt>setTickCount</tt>. It
    ** is ignored when tick positions and their labels are
    ** explicitly specified via <tt>addTick</tt>.
    **
    ** @see #setTickCount setTickCount
    ** @see #addTick(double) addTick(double)
    ** @see #addTick(double,String) addTick(double,String)
    ** @see #addTick(double,String,int,int) addTick(double,String,int,int)
    ** @see #addTick(double,Widget) addTick(double,Widget)
    ** @see #addTick(double,Widget,int,int) addTick(double,Widget,int,int)
    **
    ** @param ticksPerLabel the ratio of the number of ticks,
    **  to the number of labeled ticks.
    **
    *"""
    def setTicksPerLabel(self, ticksPerLabel):
        self.chartDecorationsChanged = True
        if ticksPerLabel <= 0:
            raise IllegalArgumentException("ticksPerLabel=" +
                        ticksPerLabel + "; ticksPerLabel must be > 0")

        self.ticksPerLabel = ticksPerLabel


    """*
    * Sets this axis' tick length. Set the tick length to zero to
    * eliminate the tick entirely.
    * <p>
    *
    *
    * @param tickLength the length of the tick.
    *
    * @see #getTickLength getTickLength
    * @see #setTickThickness setTickThickness
    * @see #setTickLabelPadding setTickLabelPadding
    * @see #setTickLocation setTickLocation
    *
    """
    def setTickLength(self, tickLength):
        pass


    """*
    * Specifies the location of the tick marks relative to this
    * axis, namely, if tick marks are outside, inside, or
    * centered on this axis.
    * <p>
    *
    * @see #getTickLocation getTickLocation
    * @see #setTickThickness setTickThickness
    * @see #setTickLength setTickLength
    * @see #setTickLabelPadding setTickLabelPadding
    *
    * @param tickLocation Specify either
    * <tt>TickLocation.INSIDE</tt>,
    * <tt>TickLocation.OUTSIDE</tt>, or
    * <tt>TickLocation.CENTERED</tt>
    *
    """
    def setTickLocation(self, tickLocation):
        self.tickLocation = tickLocation
        self.chartDecorationsChanged = True
        sym = self.getSystemCurve(self.ticksId).getSymbol()
        if self.isHorizontalAxis:
            sym.setSymbolType(tickLocation.getXAxisSymbolType(self.axisPosition))
            sym.setHeight(self.getActualTickLength())

        else:
            sym.setSymbolType(tickLocation.getYAxisSymbolType(self.axisPosition))
            sym.setWidth(self.getActualTickLength())




    """*
    * Sets this axis' tick thickness.
    * <p>
    *
    * @param tickThickness the thickness of the tick.
    *
    * @see #getTickThickness getTickThickness
    * @see #setTickLength setTickLength
    * @see #setTickLabelPadding setTickLabelPadding
    * @see #setTickLocation setTickLocation
    *
    """
    def setTickThickness(self, tickThickness):
        pass

    def maybePopulateTicks(self):
        if self.tickCount != NAI:
            self.populateTicks()



    # fills in the tick positions when auto-generated.
    def populateTicks(self):
        self.getSystemCurve(self.ticksId).clearPoints()
        #TODO: It should be possible to control the visibility of each axis,
        # including ticks and tick labels, independent of the specifications of
        # the tick marks on that axis, and independent of if any curves are
        # mapped to that axis or not.  A setVisible(Boolean isVisible) as a
        # three-way, with None being the current, dependent, defaults, and
        # TRUE, FALSE explicitly making the entire axis, including tick marks
        # and labels visible or not without having to zero the tick count, add
        # dummy curve to the axis, etc. to control axis visibility is needed.
        # x, y ticks are drawn even
        # if no curves are on these axes
        if XTICKS_ID == self.ticksId  or  YTICKS_ID == self.ticksId  or  0 < self.getNCurvesVisibleOnAxis():
            l = self.getAxisLimits()
            for i in range(self.tickCount):
                # linear interpolation between min and max
                if (self.tickCount == 1):
                    position = l.max
                else:
                    position = ((l.min * ((self.tickCount-1)-i) + i * l.max)/
                                (self.tickCount-1.0))
                self.addTickAsPoint(position,
                            (0 == i % self.ticksPerLabel) and
                                    self.formatAsTickLabel(position) or None,
                            None,
                            NAI, NAI)





    # fills in the gridlines; ticks are assumed already populated
    def populateGridlines(self):
        cTicks = self.getSystemCurve(self.ticksId)
        cGridlines = self.getSystemCurve(self.gridlinesId)
        cGridlines.clearPoints()
        nTicks = cTicks.getNPoints()
        for iTick in range(nTicks):
            if self.hasGridlines  and  (iTick % self.ticksPerGridline) == 0:
                p = cTicks.getPoint(iTick)
                cGridlines.addPoint(p.getX(), p.getY())


    def _getAxisLimits(self, result):
        # so we get 1-unit changes between adjacent ticks
        DEFAULT_AXIS_RANGE = DEFAULT_TICK_COUNT-1
        min = self.getAxisMin()
        max = self.getAxisMax()
        # Adjust min/max so that special cases, like one-point
        # charts, do not have axes that shrink down to a point,
        # which would create numerical and visual difficulties.
        if (Double.NaN==(min))  and  (Double.NaN==(max)):
            # e.g. no data and no explicitly specified ticks
            min = 0
            max = min + DEFAULT_AXIS_RANGE

        elif (Double.NaN==(min))  and  not (Double.NaN==(max)):
            # e.g. no data but only max explicitly set
            min = max - DEFAULT_AXIS_RANGE

        elif not (Double.NaN==(min))  and  (Double.NaN==(max)):
            # e.g. no data but only min explicitly set
            max = min + DEFAULT_AXIS_RANGE

        elif min == max:
            # e.g one data point only, or they set min=max
            max = min + DEFAULT_AXIS_RANGE

        result.min = min
        result.max = max

    def getAxisLimits(self):
        self._getAxisLimits(self.currentLimits)
        return self.currentLimits


    def rememberLimits(self):
        self._getAxisLimits(self.previousLimits)

    def limitsChanged(self):
        return not self.getAxisLimits().equals(self.previousLimits)


    """ similar to getTickText, except for the tick position """
    def getTickPosition(self, c, iTick):
        if self.isHorizontalAxis:
            result = c.getPoint(iTick).getX()

        else:
            result = c.getPoint(iTick).getY()

        return result


    # returns the largest, explicitly specified, tick position
    def getTickMax(self):
        result = -Double.MAX_VALUE
        c = self.getSystemCurve(self.ticksId)
        nTicks = c.getNPoints()
        for i in range(nTicks):
            result = max(result, self.getTickPosition(c, i))
        return result


    # returns the smallest, explicitly specified, tick position
    def getTickMin(self):
        result = Double.MAX_VALUE
        c = self.getSystemCurve(self.ticksId)
        nTicks = c.getNPoints()
        for i in range(nTicks):
            result = min(result, self.getTickPosition(c, i))
        return result



    # Same as max, except treats NaN/MAX_VALUE values as "not there"
    def maxIgnoreNaNAndMaxValue(self, x1, x2):
        if Double.NaN==(x1)  or  Double.MAX_VALUE == x1  or  -Double.MAX_VALUE == x1:
            result = x2

        elif Double.NaN==(x2)  or  Double.MAX_VALUE == x2  or  -Double.MAX_VALUE == x2:
            result = x1

        else:
            result = max(x1, x2)

        return result

    # Same as min, except treats NaN/MAX_VALUE values as "not there"
    def minIgnoreNaNAndMaxValue(self, x1, x2):
        if Double.NaN==(x1)  or  Double.MAX_VALUE == x1  or  -Double.MAX_VALUE == x1:
            result = x2

        elif Double.NaN==(x2)  or  Double.MAX_VALUE == x2  or  -Double.MAX_VALUE == x2:
            result = x1

        else:
            result = min(x1, x2)

        return result

    # does a dummy set of any dynamically determined axis
    # limit, so, for update purposes, they are considered
    # to have changed.
    def invalidateDynamicAxisLimits(self):
        if (Double.NaN==(axisMin)):
            self.setAxisMin(axisMin)

        if (Double.NaN==(axisMax)):
            self.setAxisMax(axisMax)


"""* The x-axis of a GChart.
*
* @see GChart#getXAxis getXAxis
"""

class XAxis(Axis):
    def __init__(self, chart):
        Axis.__init__(self, chart)
        self.isHorizontalAxis = True
        self.ticksId = XTICKS_ID
        self.gridlinesId = XGRIDLINES_ID
        self.axisId = XAXIS_ID
        self.axisPosition = -1
        self.tickLabelFormatType = None
        self.setTickLocation(TickLocation.DEFAULT_TICK_LOCATION)
        self.setTickThickness(DEFAULT_TICK_THICKNESS)
        self.setTickLength(DEFAULT_TICK_LENGTH)


    def clientToModel(clientCoordinate):
        xPixel = (Window.getScrollLeft() + clientCoordinate -
                self.chart.plotPanel.getAbsoluteLeft())
        result = self.chart.plotPanel.xChartPixelToX(xPixel)
        return result

    def getAxisLabelThickness(self):
        EXTRA_CHARHEIGHT = 2; # 1-char space above & below
        DEF_CHARHEIGHT = 1
        result = 0
        if None == self.getAxisLabel():
            result = 0

        elif NAI != self.axisLabelThickness:
            result = self.axisLabelThickness

        elif hasattr(self.getAxisLabel(), "getHTML"):
            charHeight = htmlHeight( self.getAxisLabel().getHTML())
            result = int (round((EXTRA_CHARHEIGHT+charHeight) *
                                self.getTickLabelFontSize() *
                                TICK_CHARHEIGHT_TO_FONTSIZE_LOWERBOUND))

        else:
            result = int (round(
                        (EXTRA_CHARHEIGHT + DEF_CHARHEIGHT) *
                        self.getTickLabelFontSize() *
                        TICK_CHARWIDTH_TO_FONTSIZE_LOWERBOUND))

        return result

    def getDataMax(self):
        result = -Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            nPoints = c.getNPoints()
            for j in range(nPoints):
                result = self.maxIgnoreNaNAndMaxValue(result,
                                    c.getPoint(j).getX())


        if result == -Double.MAX_VALUE:
            return Double.NaN
        return result

    def getDataMin(self):
        result = Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            nPoints = c.getNPoints()
            for j in range(nPoints):
                result = self.minIgnoreNaNAndMaxValue(result, c.getPoint(j).getX())


        if result == Double.MAX_VALUE:
            return Double.NaN
        return result


    def getMouseCoordinate(self):
        result = self.chart.plotPanel.xChartPixelToX(self.chart.plotPanel.getXMouse())
        return result


    def getTickLabelThickness(self, needsPopulation=True):
        # overrides base class
        if self.tickLabelThickness != NAI:
            result = self.tickLabelThickness

        elif self.getTickCount() == 0:
            result = 0

        else:
            # XXX: single line labels assumed; these have height
            # almost equal to the fontSize in pixels. Not really
            # right, since multi-line HTML can now be used, but user
            # can explicitly change tick label thickness with
            # multi-line, HTML based, ticks, so OK for now.
            result = int (round(
                            TICK_CHARHEIGHT_TO_FONTSIZE_LOWERBOUND *
                            self.tickLabelFontSize))

        return result


    def modelToClient(self, modelCoordinate):
        xPixel = self.chart.plotPanel.xToChartPixel(modelCoordinate)
        result = (self.chart.plotPanel.getAbsoluteLeft()
                        - Window.getScrollLeft() + xPixel )
        return result

    def modelToPixel(self, modelCoordinate):
        result = self.chart.plotPanel.xToChartPixel(modelCoordinate)
        return result

    def modelToPlotAreaPixel(self, modelCoordinate):
        result = self.chart.plotPanel.xToPixel(modelCoordinate)
        return result

    def pixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.xChartPixelToX(pixelCoordinate)
        return result

    def plotAreaPixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.xPixelToX(pixelCoordinate)
        return result

    def setTickLength(self, tickLength):
        self.chartDecorationsChanged = True
        self.tickLength = tickLength
        self.getSystemCurve(self.ticksId).getSymbol().setHeight(
        self.getActualTickLength())

    def setTickThickness(self, tickThickness):
        self.tickThickness = tickThickness
        self.getSystemCurve(self.ticksId).getSymbol().setWidth(tickThickness)



 # INDENT ERROR} end of class XAxis
"""* The right, or "y2", axis of a GChart.
*
* @see GChart#getY2Axis getY2Axis
"""

class Y2Axis(Axis):
    def __init__(self, chart):
        Axis.__init__(self, chart)
        self.isHorizontalAxis = False
        self.ticksId = Y2TICKS_ID
        self.gridlinesId = Y2GRIDLINES_ID
        self.axisId = Y2AXIS_ID
        self.axisPosition = 1
        self.setTickLocation(TickLocation.DEFAULT_TICK_LOCATION)
        self.setTickThickness(DEFAULT_TICK_THICKNESS)
        self.setTickLength(DEFAULT_TICK_LENGTH)

    def clientToModel(clientCoordinate):
        yPixel = (Window.getScrollTop() + clientCoordinate -
                        self.chart.plotPanel.getAbsoluteTop())
        result = self.chart.plotPanel.yChartPixelToY2(yPixel)
        return result

    def getDataMax(self):
        result = -Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            if c.getYAxis() == Y2_AXIS:
                nPoints = c.getNPoints()
                for j in range(nPoints):
                    result = self.maxIgnoreNaNAndMaxValue(result,
                                                        c.getPoint(j).getY())



        if result == -Double.MAX_VALUE:
            return Double.NaN
        return result

    def getDataMin(self):
        result = Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            if c.getYAxis() == Y2_AXIS:
                nPoints = c.getNPoints()
                for j in range(nPoints):
                    result = self.minIgnoreNaNAndMaxValue(result,
                                                    c.getPoint(j).getY())


        if result == Double.MAX_VALUE:
            return Double.NaN
        return result


    def getMouseCoordinate(self):
        result = self.chart.plotPanel.yChartPixelToY2(self.chart.plotPanel.getYMouse())
        return result


    def modelToClient(self, modelCoordinate):
        yPixel = self.chart.plotPanel.yToChartPixel(modelCoordinate, True)
        result = self.chart.plotPanel.getAbsoluteTop() - Window.getScrollTop() + yPixel
        return result

    def modelToPixel(self, modelCoordinate):
        result = self.chart.plotPanel.yToChartPixel(modelCoordinate, True)
        return result

    def modelToPlotAreaPixel(self, modelCoordinate):
        result = self.chart.plotPanel.yToPixel(modelCoordinate, True)
        return result

    def pixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.yChartPixelToY2(pixelCoordinate)
        return result

    def plotAreaPixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.yPixelToY2(pixelCoordinate)
        return result

    def setTickLength(self, tickLength):
        self.chartDecorationsChanged = True
        self.tickLength = tickLength
        self.getSystemCurve(self.ticksId).getSymbol().setWidth(self.getActualTickLength())

    def setTickThickness(self, tickThickness):
        self.tickThickness = tickThickness
        self.getSystemCurve(self.ticksId).getSymbol().setHeight(tickThickness)


"""* The left y-axis of a GChart.
*
* @see GChart#getYAxis getYAxis
*
"""

class YAxis(Axis):
    def __init__(self, chart):
        Axis.__init__(self, chart)
        self.isHorizontalAxis = False
        self.ticksId = YTICKS_ID
        self.gridlinesId = YGRIDLINES_ID
        self.axisId = YAXIS_ID
        self.axisPosition = -1
        self.setTickLocation(TickLocation.DEFAULT_TICK_LOCATION)
        self.setTickThickness(DEFAULT_TICK_THICKNESS)
        self.setTickLength(DEFAULT_TICK_LENGTH)

    def clientToModel(clientCoordinate):
        yPixel = (Window.getScrollTop() + clientCoordinate -
                        self.chart.plotPanel.getAbsoluteTop())
        result = self.chart.plotPanel.yChartPixelToY(yPixel)
        return result

    def getDataMax(self):
        result = -Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            if c.getYAxis() == Y_AXIS:
                nPoints = c.getNPoints()
                for j in range(nPoints):
                    result = self.maxIgnoreNaNAndMaxValue(result,
                    c.getPoint(j).getY())



        if result == -Double.MAX_VALUE:
            return Double.NaN
        return result

    def getDataMin(self):
        result = Double.MAX_VALUE
        nCurves = self.chart.getNCurves()
        for i in range(nCurves):
            c = self.getSystemCurve(i)
            if not c.isVisible():
                continue

            if c.getYAxis() == Y_AXIS:
                nPoints = c.getNPoints()
                for j in range(nPoints):
                    result = self.minIgnoreNaNAndMaxValue(result,
                    c.getPoint(j).getY())



        if result == Double.MAX_VALUE:
            return Double.NaN
        return result


    def getMouseCoordinate(self):
        result = self.chart.plotPanel.yChartPixelToY(self.chart.plotPanel.getYMouse())
        return result



    def modelToClient(self, modelCoordinate):
        yPixel = self.chart.plotPanel.yToChartPixel(modelCoordinate, False)
        result = self.chart.plotPanel.getAbsoluteTop() - Window.getScrollTop() + yPixel
        return result

    def modelToPixel(self, modelCoordinate):
        result = self.chart.plotPanel.yToChartPixel(modelCoordinate, False)
        return result

    def modelToPlotAreaPixel(self, modelCoordinate):
        result = self.chart.plotPanel.yToPixel(modelCoordinate, False)
        return result

    def pixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.yChartPixelToY(pixelCoordinate)
        return result

    def plotAreaPixelToModel(self, pixelCoordinate):
        result = self.chart.plotPanel.yPixelToY(pixelCoordinate)
        return result

    def setTickLength(self, tickLength):
        self.chartDecorationsChanged = True
        self.tickLength = tickLength
        self.getSystemCurve(self.ticksId).getSymbol().setWidth(
                                self.getActualTickLength())

    def setTickThickness(self, tickThickness):
        self.tickThickness = tickThickness
        self.getSystemCurve(self.ticksId).getSymbol().setHeight(tickThickness)

