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
from pyjamas.chart import Double


from pyjamas.ui.Image import Image

from pyjamas.chart import AnnotationLocation
from pyjamas.chart import GChartUtil

from pyjamas.chart import GChartConsts

# Use smallest min band size, since I expect per band
# cost to be small compared to per-point hit testing.
MIN_BAND_SIZE = 1

"""*
** Specifies the type of symbol used by a curve. GChart
** includes a <tt>LINE</tt> symbol type (suitable for solidly
** connected line charts), various "box" symbol types
** (suitable for scatter and dotted-line charts),
** horizontal and vertical bars that extend to axis limits
** or a specified baseline (suitable for bar and area charts),
** and pie slices (suitable for pie charts) in these
** symbol types. Thus, choosing a curve's symbol type has a
** bigger impact on the kind of chart you create than in
** other charting APIs you may have used.
**
** <p> One advantage of this symbol type based approach: you
** can place multiple pies, lines and/or bars on a single
** chart simply by creating multiple curves whose associated
** symbols have appropriately different symbol types.
**
** <p> Note that, for line, area, or pie charts, the exact
** look of the non-rectangular aspects (connecting lines,
** filled-in areas, etc.) of these symbols in the chart is
** largely governed by the host <tt>Symbol</tt>'s
** <tt>fillSpacing</tt> and <tt>fillThickness</tt>
** properties.
**
** <p> For instance, with the default <tt>fillThickness</tt>
** of 0 for the <tt>BOX_CENTER</tt> symbol, curves display
** only explicitly specified data points, without any
** connecting lines between them. But, if you set
** <tt>fillThickness</tt> to 1, GChart interpolates a series
** of 1 pixel by 1 pixel rectangular "dots" between successive
** data points, with an intra-dot spacing defined by the
** symbol's <tt>fillSpacing</tt> setting.  <p>
**
** Since v2.5, a <tt>fillSpacing==0</tt> setting, with the
** special meaning of "continuous filling", is allowed. If an
** external canvas library has been plugged into GChart via
** <tt>setCanvasFactory</tt>,
** higher quality, continuously filled pie, line, and area charts
** can be produced via the combination: <tt>fillSpacing==0</tt> and
** <tt>fillThickness > 0</tt> along with one of the pie, line, or
** bar symbol types described below.<p>
**
** You must select each curve's symbol type from the predefined
** set of supported types listed in the "Field Summary"
** section below. The default symbol type is <tt>BOX_CENTER</tt>.
**
** @see Curve#getSymbol getSymbol
** @see Symbol#setSymbolType setSymbolType
** @see Symbol#setFillSpacing setFillSpacing
** @see Symbol#setFillThickness setFillThickness
** @see Symbol Symbol
**
*"""
class SymbolType:

    """
    * For efficiency during hit testing, points get separated
    * into bins associated with adjacent vertical
    * (or horizontal) bands that cover the plot area.
    * <p>
    *
    * Subclasses (such as those for producing horizontal bar
    * charts) whose rendered symbols do not have a fixed width
    * across all the points on a single curve, MUST set this
    * field to True within their constructors, because
    * the hit testing approach assumes fixed "thickness"
    * symbols for simplicity/efficiency.
    * <p>
    *
    * Subclasses that have both a fixed width and height MAY
    * set this to True if they are typically used in a way
    * that tends to make horizontal banding a better (= tends
    * to place same # of points in each band) binning strategy.
    *
    * <p>
    *
    * If <tt>None</tt>, GChart uses a simple heuristic that assumes
    * that a brush that is wider than high implies developer is
    * trying to let user distinguish finer y differences, and thus
    * our bands should separate points more finely (and hence allow
    * for faster band-indexed hit testing) if we use horizontal
    * banding in this case (and vertical otherwise).
    * <p>
    *
    * See the <tt>bandSeparatePoints</tt> method for more info.
    *
    """
    def isHorizontallyBanded(self):
        return self.horizontallyBanded

    """ Thickness (in pixels) of hit-test-bands used with this
    * symbol type.
    * <p>
    *
    * Gets overriden for pie slice symbol types, which base
    * thickness on pie diameter.
    """
    def getBandThickness(self, pp, sym, onY2):
        if sym.isHorizontallyBanded():
            result = max(MIN_BAND_SIZE, sym.getHeight(pp, onY2))

        else:
            result = max(MIN_BAND_SIZE, sym.getWidth(pp))

        return result


    # is overridden by pie slices, which use a different brush shape
    def getBrushHeight(self, sym):
        result = sym.getBrushHeight()
        return result

    # again, so pie slices can override
    def getBrushLocation(self, sym):
        result = sym.getBrushLocation()
        return result

    # is overridden by pie slices, which use a different brush shape
    def getBrushWidth(self, sym):
        result = sym.getBrushWidth()
        return result

    # play similar role as same-named fields of AnnotationLocation
    """
    * If a symbol's left, right, top, or bottom edge
    * represents the x or y location associated with this
    * symbol, the corresponding pixel paddings are 0.
    *
    * If a position 1/2 pixel to the right, left, below, or
    * above (respectively) those edges represents the position
    * of the x or y in question, the values are 0.5.
    *
    * Why is this needed? Because GChart uses 1 px gridlines
    * whose center represents the point associated with the
    * gridline, and to get a corresponding edge to perfectly
    * overlay a gridline when its associated position is
    * the same as that gridline, we need to associated the
    * position of the represented x or y coordinate not
    * with the symbol's box edge itself, but rather
    * with a position 1/2 px towards the center of the
    * symbol. If you don't specify an extra half pixel
    * for, say, a vertical bar, it won't align right
    * on top of gridlines when it has the same height
    * as the associated gridline.
    * <p>
    *
    * In effect, we deliberately add a 1/2 px error to
    * certain symbols so that they appear to line up
    * perfectly with the gridlines.
    *
    """

    # symbols are part of the internals of a GChart,
    # so only we should instantiate them.
    def __init__(self, widthMultiplier, heightMultiplier,
                        pixelPadLeft, pixelPadRight, 
                        pixelPadTop, pixelPadBottom,
                        isHorizontallyBanded=None):
        AnnotationLocation.validateMultipliers(widthMultiplier,
                                               heightMultiplier)
        self.widthMultiplier = widthMultiplier
        self.heightMultiplier = heightMultiplier
        self.pixelPadLeft = pixelPadLeft
        self.pixelPadRight = pixelPadRight
        self.pixelPadTop = pixelPadTop
        self.pixelPadBottom = pixelPadBottom
        self.horizontallyBanded = isHorizontallyBanded
        self.oppositeEdge = Double.NaN


    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return height


    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return width


    """
    * Pixel x-coordinate at center of bounding rectangle surrounding
    * given symbol rendered with this symbol type.
    * <p>
    *
    * This method defines the x-coordinate of the rendered
    * symbol's center-point (used for hit testing purposes) for all
    * symbols except pie slices.
    *
    """
    def getCenterX_2(self, pp, symbol, prevX, x, nextX):
        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)
        xPx = pp.xToPixel(x)
        prevXPx = pp.xToPixel(prevX)
        nextXPx = pp.xToPixel(nextX)
        width = symbol.getWidth(pp)

        symWidth = self.getAdjustedWidth(width, xPx,
                                prevXPx, nextXPx,
                                xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return Double.NaN


        xLeft = self.getUpperLeftX(width, xPx,
                            prevXPx, nextXPx,
                            xMinPx, xMaxPx, xMidPx,
                            pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return Double.NaN


        xCenter = xLeft + symWidth/2.

        return xCenter



    """
    * Pixel x-coordinate at center of the symbol, used for
    * hit-testing purposes by rectangular symbol types.
    * <p>
    *
    * Overridden by pie slice symbol types.
    *
    """
    def getCenterX(self, pp, symbol, iPoint):

        c = symbol.getParent()
        p  = c.getPoint(iPoint)
        prevX = Double.NaN
        x = p.getX()
        nextX = Double.NaN
        if iPoint > 0:
            prevX = c.getPoint(iPoint-1).getX()

        if iPoint+1 < c.getNPoints():
            nextX = c.getPoint(iPoint+1).getX()


        result = self.getCenterX_2(pp, symbol, prevX, x, nextX)

        return result



    """
    * Pixel y-coordinate at center of bounding rectangle surrounding
    * given symbol rendered with this symbol type.
    * <p>
    *
    * This method defines the y-coordinate of the rendered
    * symbol's center-point (used for hit testing purposes) for all
    * symbols except pie slices.
    *
    """
    def getCenterY_2(self, pp, symbol, prevY, y, nextY, onY2):

        # the cartesian data and pixel Y coordinates are
        # flipped, hence the (counter-intuitive) min/max
        # interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)
        yPx = pp.yToPixel(y, onY2)
        prevYPx = pp.yToPixel(prevY, onY2)
        nextYPx = pp.yToPixel(nextY, onY2)
        height = symbol.getHeight(pp, onY2)

        symHeight = self.getAdjustedHeight(height, yPx,
        prevYPx, nextYPx, yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return Double.NaN


        yTop = self.getUpperLeftY(height, yPx,
        prevYPx, nextYPx,
        yMinPx, yMaxPx, yMidPx,
        pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return Double.NaN


        yCenter =  yTop + symHeight/2.

        return yCenter



    """
    * Pixel y-coordinate at center of the symbol, used for
    * hit-testing purposes by rectangular symbol types.
    * <p>
    *
    * Overridden by pie slice symbol types.
    *
    """
    def getCenterY(self, pp, symbol, iPoint, onY2):

        c = symbol.getParent()
        p = c.getPoint(iPoint)
        prevY = Double.NaN
        y = p.getY()
        nextY = Double.NaN
        if iPoint > 0:
            prevY = c.getPoint(iPoint-1).getY()

        if iPoint+1 < c.getNPoints():
            nextY = c.getPoint(iPoint+1).getY()


        result = self.getCenterY_2(pp, symbol, prevY, y, nextY, onY2)

        return result


    # pixel coordinate of left edge of symbol if rendered at given x
    # Note: this can actually be the right edge if the symbol
    # width is negative, as can occur with baseline-based bars
    def getEdgeLeft(self, pp, symbol, x, onY2):
        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)
        xPx = pp.xToPixel(x)
        prevXPx = Double.NaN
        nextXPx = Double.NaN
        width = symbol.getWidth(pp)

        symWidth = self.getAdjustedWidth(width, xPx,
        prevXPx, nextXPx,
        xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return Double.NaN


        xLeft = self.getUpperLeftX(width, xPx,
                                prevXPx, nextXPx,
                                xMinPx, xMaxPx, xMidPx,
                                pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return Double.NaN

        result = xLeft
        return result


    # pixel coordinate of right edge of symbol if rendered at given x
    # Note: this can actually be the left edge if the symbol
    # width is negative, as can occur with baseline-based bars
    def getEdgeRight(self, pp, symbol, x, onY2):
        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)
        xPx = pp.xToPixel(x)
        prevXPx = Double.NaN
        nextXPx = Double.NaN
        width = symbol.getWidth(pp)

        symWidth = self.getAdjustedWidth(width, xPx,
                                        prevXPx, nextXPx,
                                        xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return Double.NaN


        xLeft = self.getUpperLeftX(width, xPx,
                                    prevXPx, nextXPx,
                                    xMinPx, xMaxPx, xMidPx,
                                    pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return Double.NaN


        result = xLeft + symWidth

        return result




    # pixel coordinate of top edge of symbol if rendered at given y
    # Note: this can actually be the bottom edge if the symbol
    # width is negative, as can occur with baseline-based bars
    def getEdgeTop(self, pp, symbol, y, onY2):

        # the cartesian data and pixel Y coordinates are
        # flipped, hence the (counter-intuitive) min/max
        # interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)
        yPx = pp.yToPixel(y, onY2)
        prevYPx = Double.NaN
        nextYPx = Double.NaN
        height = symbol.getHeight(pp, onY2)

        symHeight = self.getAdjustedHeight(height, yPx,
                            prevYPx, nextYPx, yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return Double.NaN


        yTop = self.getUpperLeftY(height, yPx,
                                prevYPx, nextYPx,
                                yMinPx, yMaxPx, yMidPx,
                                pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return Double.NaN


        result = yTop

        return result




    # pixel coordinate of bottom edge of symbol if rendered at given y
    # Note: this can actually be the top edge if the symbol
    # width is negative, as can occur with baseline-based bars
    def getEdgeBottom(self, pp, symbol, y, onY2):

        # the cartesian data and pixel Y coordinates are
        # flipped, hence the (counter-intuitive) min/max
        # interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)
        yPx = pp.yToPixel(y, onY2)
        prevYPx = Double.NaN
        nextYPx = Double.NaN
        height = symbol.getHeight(pp, onY2)

        symHeight = self.getAdjustedHeight(height, yPx,
                            prevYPx, nextYPx, yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return Double.NaN


        yTop = self.getUpperLeftY(height, yPx,
                            prevYPx, nextYPx,
                            yMinPx, yMaxPx, yMidPx,
                            pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return Double.NaN


        result = yTop+symHeight

        return result



    # gets edge that is furthest away from the point, horizontally
    # Note: for bar charts, this is the edge of the symbol
    # along the y-axis, y2-axis, or vertical baseline.
    def getEdgeOppositeHorizontally(self, pp, symbol, x, onY2):
        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)
        xPx = pp.xToPixel(x)
        prevXPx = Double.NaN
        nextXPx = Double.NaN
        width = symbol.getWidth(pp)

        symWidth = self.getAdjustedWidth(width, xPx,
                                    prevXPx, nextXPx,
                                    xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return Double.NaN


        xLeft = self.getUpperLeftX(width, xPx,
                                    prevXPx, nextXPx,
                                    xMinPx, xMaxPx, xMidPx,
                                    pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return Double.NaN


        result = xLeft + symWidth
        if abs(xLeft - xPx) > abs(result - xPx):
            result = xLeft

        return result



    # gets edge that is furthest away from the point, vertically
    # Note: for bar charts, this is the edge of the symbol
    # along the x-axis, x2-axis, or horizontal baseline.
    def getEdgeOppositeVertically(self, pp, symbol, y, onY2):

        # the cartesian data and pixel Y coordinates are
        # flipped, hence the (counter-intuitive) min/max
        # interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)
        yPx = pp.yToPixel(y, onY2)
        prevYPx = Double.NaN
        nextYPx = Double.NaN
        height = symbol.getHeight(pp, onY2)

        symHeight = self.getAdjustedHeight(height, yPx,
                                prevYPx, nextYPx, yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return Double.NaN


        yTop = self.getUpperLeftY(height, yPx,
                                prevYPx, nextYPx,
                                yMinPx, yMaxPx, yMidPx,
                                pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return Double.NaN


        result = yTop+symHeight
        if abs(yTop - yPx) > abs(result - yPx):
            result = yTop


        return result



    """
    * Determines if a symbol, rendered at the specified
    * position (and with the given positions of the previous
    * and subsequent points, and the y-axis on which it is
    * rendered) intersects with a given rectangle.
    *
    """
    def isIntersecting13(self, pp, symbol, prevX, x, nextX, prevY, y,
                            nextY, onY2, top, right, bottom, left):

        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)
        xPx = pp.xToPixel(x)
        prevXPx = pp.xToPixel(prevX)
        nextXPx = pp.xToPixel(nextX)
        width = symbol.getWidth(pp)

        symWidth = self.getAdjustedWidth(width, xPx,
                                        prevXPx, nextXPx,
                                        xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return False


        xLeft = self.getUpperLeftX(width, xPx,
                                    prevXPx, nextXPx,
                                    xMinPx, xMaxPx, xMidPx,
                                    pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return False


        # note: symWidth can be negative.
        if max(xLeft, xLeft + symWidth) < left:
            return False;  # symbol is entirely to left of rectangle

        elif min(xLeft, xLeft + symWidth) > right:
            return False; # symbol is entirely to right of rectangle

        # else brush and symbol have overlapping x-intervals

        # the cartesian data and pixel Y coordinates are flipped,
        # hence the (counter-intuitive) min/max interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)
        yPx = pp.yToPixel(y, onY2)
        prevYPx = pp.yToPixel(prevY, onY2)
        nextYPx = pp.yToPixel(nextY, onY2)
        height = symbol.getHeight(pp, onY2)

        symHeight = self.getAdjustedHeight(height, yPx,
                                prevYPx, nextYPx, yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return False


        yTop = self.getUpperLeftY(height, yPx,
                            prevYPx, nextYPx,
                            yMinPx, yMaxPx, yMidPx,
                            pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return False


        # note: symHeight can be negative.
        if max(yTop, yTop + symHeight) < top:
            return False; # symbol is entirely above rectangle

        elif min(yTop, yTop + symHeight) > bottom:
            return False; # symbol is entirely below the rectangle

        # else rectangle and symbol have overlapping y-intervals

        # overlapping x and y intervals ==> rectangle intersects symbol
        return True



    """
    * Determines if a symbol, when rendered at a given point,
    * intersects with a "rectangular brush".
    * <p>
    *
    * This brush is typically centered at the current mouse
    * position, and allows the user to select the point on a
    * curve, the pie slice, etc. for which hover feedback will
    * be displayed.
    * <p>
    *
    * This method gets overridden for pie slices (due to
    * their non-rectangular shape).
    *
    """
    def isIntersecting(self, pp, symbol, iPoint, onY2, xBrush,
                             yBrush, brushWidth, brushHeight):

        c = symbol.getParent()
        p = c.getPoint(iPoint)
        prevX = Double.NaN
        x = p.getX()
        nextX = Double.NaN
        prevY = Double.NaN
        y = p.getY()
        nextY = Double.NaN
        if iPoint > 0:
            prevX = c.getPoint(iPoint-1).getX()
            prevY = c.getPoint(iPoint-1).getY()

        if iPoint+1 < c.getNPoints():
            nextX = c.getPoint(iPoint+1).getX()
            nextY = c.getPoint(iPoint+1).getY()


        # Treat mouse cursor as if it were a 0x0 pixel symbol
        # centered at xBrush, yBrush to which an annotation of
        # the width, height of the brush is attached.
        top = symbol.getBrushLocation().getUpperLeftY(yBrush, brushHeight, 0)
        bottom = top + brushHeight
        left = symbol.getBrushLocation().getUpperLeftX(xBrush, brushWidth, 0)
        right = left + brushWidth

        result = self.isIntersecting13(pp, symbol,
                                prevX, x, nextX,
                                prevY, y, nextY, onY2,
                                top, right, bottom, left)

        return result



    # width of border of symbol displayed in legend key
    def getIconBorderWidth(self, legendFontSize, symBorderFraction):
        result = 0
        if symBorderFraction > 0:
            result = int( max(1.0, math.floor(
                                    symBorderFraction * min(
                                    self.getIconWidth(legendFontSize),
                                    self.getIconHeight(legendFontSize)))))

        return result

    def getIconHeight(self, legendFontSize):
        return int (round(0.75*legendFontSize))


    def getIconWidth(self, legendFontSize):
        return int (round(0.75*legendFontSize))



    def getUpperLeftX(self, width, x, xPrev, xNext, xMin, xMax, xMid, xMouse):
        adjWidth = self.getAdjustedWidth(width, x,
                                    xPrev, xNext, xMin, xMax, xMid)
        result = x + (0.5*(self.widthMultiplier - 1)) * adjWidth
        return result


    def getUpperLeftY(self, height, y, yPrev, yNext, yMin, yMax, yMid, yMouse):
        adjHeight = self.getAdjustedHeight(height, y,
                                      yPrev, yNext, yMin, yMax, yMid)
        result = y + (0.5*(self.heightMultiplier - 1)) * adjHeight
        return result



    def defaultAnnotationLocation(self):
        #         return AnnotationLocation.SOUTH
        result = self.defaultHoverLocation()
        return result

    # fillSpacing to use when a symbol's fillSpacing is Double.NaN
    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_SYMBOL_FILL_SPACING

    # fillThickness to use when a symbol's fillThickness is
    # GChartConsts.NAI
    def defaultFillThickness(self):
        return GChartConsts.DEFAULT_SYMBOL_FILL_THICKNESS

    # symbol-type-specific default hovertextTemplate
    def defaultHovertextTemplate(self):
        return GChartConsts.DEFAULT_HOVERTEXT_TEMPLATE

    # symbol-type-specific default location of hover feedback
    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_HOVER_LOCATION

    """
    * Unmanaged images. Supports older code that simply
    * zaps/recreates each image, relying on browser's garbage
    * collector to deal with the reuse issue (that's slower).
    *
    """
    def createImage(self, symbol, width, height, borderWidth, url):

        result = Image(url)
        # if smaller of width, height is at least twice
        # the border width, border width is used as is, otherwise,
        # it's replaced with half the smaller of width, height:
        if width < height:
            wh = width
        else:
            wh = height
        if (2*borderWidth <= wh):
            cappedBW = borderWidth
        else:
            cappedBW = int(wh/2)

        borderColor = symbol.getBorderColorCSS()
        # If border was too big to fit inside rectangle, since GChart
        # borders are uniform around the rectangle, odd-sized
        # dimensions can leave a single "leftover" 1px inside the
        # border. Set background to the border's color so that the
        # border, in effect, takes up the entire rectangle.
        if (cappedBW == borderWidth):
            backgroundColor = symbol.getBackgroundColorCSS()
        else:
            backgroundColor = borderColor
        # In principle, x,y position should also change with transparency
        # emulation in some cases. But these images are only used in
        # tables on the legend key, where they are always centered, so
        # that doesn't matter.

        if GChartConsts.TRANSPARENT_BORDER_COLOR == borderColor:
            #transparency emulation
            if cappedBW > 0:
                # to emulate an internal transparent border using a 0 width
                # border, we need to shrink the size by twice the amount
                # of the border.
                height -= 2*cappedBW; # shrink size
                width -= 2*cappedBW

            # else, external border is just eliminated, no adjustment needed
            cappedBW = 0
            borderColor = "transparent"
            if GChartConsts.TRANSPARENT_BORDER_COLOR == backgroundColor:
                backgroundColor = "transparent"


        elif cappedBW > 0:
            height -= 2*cappedBW; # shrink size to incorporate
            width -= 2*cappedBW; # impact of internal border.

        GChartUtil.setBackgroundColor(result, backgroundColor)
        GChartUtil.setBorderColor(result, borderColor)
        GChartUtil.setBorderStyle(result, symbol.getBorderStyle())
        GChartUtil.setBorderWidth(result, abs(cappedBW))
        result.setPixelSize(int(round(width)), int(round(height)))
        return result

    # creates small image of symbol (used in the chart legend).
    def createIconImage(self, symbol, legendFontSize, symBorderFraction):
        result = self.createImage(symbol,
                            self.getIconWidth(legendFontSize),
                            self.getIconHeight(legendFontSize),
                            self.getIconBorderWidth(legendFontSize,
                                            symBorderFraction),
                            symbol.getImageURL())
        return result


    # are two one-dimensional ranges (x1...x2 and y1...y2) disjoint?
    def areDisjointRanges(self, x1, x2, y1, y2):
        result = False
        if (x1 < y1  and  x2 < y1  and  x1 < y2  and  x2 < y2)  or  (y1 < x1  and  y2 < x1  and  y1 < x2  and  y2 < x2):
            result = True

        return result


    # do two rectangular regions intersect (left/right and/or
    # top/bottom can be interchanged and it still works)
    def intersects(self, left1, top1, right1, bottom1, left2, top2, right2, bottom2):
        result = True
        if self.areDisjointRanges(left1, right1, left2, right2)  or  self.areDisjointRanges(top1, bottom1, top2, bottom2):
            result = False

        return result



    """ renders a single image that is part of a (possibly
    * multi-image) symbol, along with that image's annotation """
    def realizeOneImageOfSymbol(self, pp, grp, arp, symbol, annotation, onY2, clipPlotArea, clipDecoratedChart, xPx, yPx, prevXPx, prevYPx, nextXPx, nextYPx, width, height):


        xMin = pp.getXMin()
        xMax = pp.getXMax()
        xMid = symbol.getBaseline()
        if (Double.NaN==(xMid)):
            xMid = (xMin + xMax)/2.

        xMinPx = pp.xToPixel(xMin)
        xMaxPx = pp.xToPixel(xMax)
        xMidPx = pp.xToPixel(xMid)

        symWidth = self.getAdjustedWidth(width, xPx,
                                        prevXPx, nextXPx,
                                        xMinPx, xMaxPx, xMidPx)
        if (Double.NaN==(symWidth)):
            return


        xLeft = self.getUpperLeftX(width, xPx,
                                    prevXPx, nextXPx,
                                    xMinPx, xMaxPx, xMidPx,
                                    pp.getXMousePlotArea())
        if (Double.NaN==(xLeft)):
            return


        xCenter = xLeft + symWidth/2.
        # the data and pixel Y coordinates are flipped, hence
        # the (counter-intuitive) min/max interchange below:
        if onY2:
            yMin =  pp.getY2Max()
            yMax =  pp.getY2Min()
        else:
            yMin =  pp.getYMax()
            yMax =  pp.getYMin()
        yMid = symbol.getBaseline()
        if (Double.NaN==(yMid)):
            yMid = (yMin + yMax)/2.

        yMinPx = pp.yToPixel(yMin,onY2)
        yMaxPx = pp.yToPixel(yMax,onY2)
        yMidPx = pp.yToPixel(yMid,onY2)

        symHeight = self.getAdjustedHeight( height, yPx,
                                            prevYPx, nextYPx,
                                            yMinPx, yMaxPx, yMidPx)
        if (Double.NaN==(symHeight)):
            return


        yTop = self.getUpperLeftY(height, yPx,
                            prevYPx, nextYPx,
                            yMinPx, yMaxPx, yMidPx,
                            pp.getYMousePlotArea())
        if (Double.NaN==(yTop)):
            return


        yCenter =  yTop + symHeight/2.

        if clipPlotArea  and  not self.intersects(xMinPx, yMinPx, xMaxPx, yMaxPx, xLeft, yTop, xLeft+symWidth, yTop+symHeight):
            return; # image is completely off plot area, so skip it.

        elif clipDecoratedChart:
            yAxisWidth = pp.getYAxisEnsembleWidth()
            titleThickness = pp.chartTitleThickness()
            if not self.intersects(xMinPx - yAxisWidth, yMinPx - titleThickness,
                              pp.getXChartSizeDecoratedQuickly()-yAxisWidth,
                              pp.getYChartSizeDecoratedQuickly()-titleThickness,
                              xLeft, yTop, xLeft+symWidth, yTop+symHeight):
                return; # image completely off decorated chart, so skip


        # translate negative width, height to equivalent
        # positive values that image tags can handle
        signWidth = 1
        if symWidth < 0:
            xLeft = xLeft + symWidth
            symWidth *= -1
            signWidth = -1

        signHeight = 1
        if symHeight < 0:
            yTop = yTop + symHeight
            symHeight *= -1
            signHeight = -1


        # Positive pixel padding pushes the specified edge
        # outward from the center by the given amount, without
        # changing the location of the center the symbol.
        # Similarly, negative padding, pushes the edge inward.

        if symWidth != 0:
            xLeft -= self.pixelPadLeft
            symWidth += self.pixelPadLeft + self.pixelPadRight

        # else, zero width, keep it that way (no padding added)

        if symHeight != 0:
            yTop -= self.pixelPadTop
            symHeight += self.pixelPadTop + self.pixelPadBottom

        # else, zero height, keep it that way (no padding added)

        borderWidth = symbol.getBorderWidth()
        # borderWidth < 0 ==> external border
        if (symWidth > 0  and  symHeight > 0)  or  borderWidth < 0:
            grp.renderBorderedImage(symbol.getBackgroundColorCSS(),
                                    symbol.getBorderColorCSS(),
                                    symbol.getBorderStyle(),
                                    borderWidth,
                                    symWidth,
                                    symHeight,
                                    xLeft, yTop, symbol.getImageURL())

        # if the image has an attached label, realize that
        if (annotation!=None  and  (annotation.getText() is not None  or
            annotation.getWidget() is not None)  and  
            annotation.getVisible()):
            loc = annotation.getLocation()
            if None == loc:
                loc = self.defaultAnnotationLocation()

            loc = AnnotationLocation.transform(loc, signWidth, signHeight)
            # Note: yShift follows orientation of cartesian y
            # Axis, which is 180 degrees different from pixel y
            # coordinates, hence the extra "-" below.
            #
            # signWidth, signHeight multipliers assure that shifts are
            # appropriately symetrical for bars above and below or to the
            # left or right of their baselines (only baseline bars use
            # negative symbol widths) For example, a yShift of
            # 10px would shift up for bars above the baseline, and down
            # for bars below the baseline, which is usually what you
            # want (e.g. placing labels above or below the bars).
            arp.renderAnnotation(annotation, loc,
                                xCenter+signWidth*annotation.getXShift(),
                                yCenter-signHeight*annotation.getYShift(),
                                symWidth, symHeight,
                                symbol)




    # Distance from the point (x1, y1) to the point (x2, y2)
    def distance(self, x1, y1, x2, y2):
        result = math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))
        return result

    """
    * Renders the symbol at the specified position within the plot
    * panel, by creating appropriately positioned Image and Label
    * objects within the given rendering panel.
    * <p>
    *
    * Most of the Image widgets will be replaced with drawing on the
    * rendering panel's dedicated canas Widget if an external canvas
    * capability has been bolted onto GChart, and continuous fill
    * (fillSpacing == 0) has been requested for the curve.
    *
    * <p>
    *
    * So-rendered symbols are used to represent: each point on a curve
    * (including any "filled" elements linearly interpolated between
    * successive points, such as, point-to-point connecting lines and
    * "areas under the curve") and (via special hidden system curves)
    * axes, gridlines, ticks, tick-labels, titles, footnotes, and
    * the legend key.
    * <p>
    *
    * This method is overridden for pie slice symbols and
    * the LINE symbol type.
    *
    """
    # retains coord of an area chart's "filled to" axis/baseline
    def realizeSymbol(self, pp, grp, arp, symbol, annotation, onY2, clipPlotArea, clipDecoratedChart, drawMainSymbol, x, y, prevX, prevY, nextX, nextY):

        if (Double.NaN==(x))  or  (Double.NaN==(y)):
            # this point undefined (isNaN)
            return


        xPx = pp.xToPixel(x)
        yPx = pp.yToPixel(y, onY2)
        prevXPx = pp.xToPixel(prevX)
        prevYPx = pp.yToPixel(prevY, onY2)
        nextXPx = pp.xToPixel(nextX)
        nextYPx = pp.yToPixel(nextY, onY2)
        spacing = symbol.getFillSpacing()
        thickness = symbol.getFillThickness()
        canvas = grp.getCanvas()

        if 0 == spacing  and  None != canvas  and  thickness > 0:
            # if canvas rendered
            if None == self.horizontallyBanded:
                """
                * Continuous fill, canvas available, and not explicitly
                * horizontally or vertically banded. For example, BOX_*
                * symbol types are not explicitly oriented, but VBAR_*
                * (vertically) and HBAR_* (horizontally) are: use canvas
                * to draw a straight line between points.  <p>
                *
                * Code in this branch also gets executed by the LINE
                * symbol type.
                *
                """
                borderWidth = symbol.getBorderWidth()
                # negative (external) border widens line by 2*|borderWidth|
                if (borderWidth >= 0):
                    externalLineWidth = thickness
                else:
                    externalLineWidth = (thickness + 2*abs(borderWidth))
                if (borderWidth >= 0):
                    internalLineWidth = max(thickness-2*borderWidth,0)
                else:
                    internalLineWidth = thickness
                borderColor = symbol.getBorderColor()
                backgroundColor = symbol.getBackgroundColor()
                if (externalLineWidth > 0  and
                   ((GChartConsts.TRANSPARENT_BORDER_COLOR != borderColor  and
                   "transparent" != borderColor)  or
                   (GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and
                   "transparent" != backgroundColor))):
                    if Double.NaN==(prevX)  or  Double.NaN==(prevY):
                        # first defined point after an undefined point ==> path
                        # (need to draw zero-thickness lines for possible line
                        # endings user may have defined by overriding beginPath)
                        canvas.beginPath()
                        canvas.moveTo(xPx - grp.x0, yPx - grp.y0)

                    if Double.NaN==(nextX)  or  Double.NaN==(nextY):
                        # last defined point before undefined point ==> draw accumulated path
                        if (GChartConsts.TRANSPARENT_BORDER_COLOR != borderColor  and
                           "transparent" != borderColor  and
                           externalLineWidth > 0):
                            canvas.setStrokeStyle(borderColor)
                            canvas.setLineWidth(externalLineWidth)
                            canvas.stroke()

                        if GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and  "transparent" != backgroundColor  and  internalLineWidth > 0:
                            canvas.setLineWidth(internalLineWidth)
                            canvas.setStrokeStyle(backgroundColor)
                            canvas.stroke()


                    else:# not at end of chain ==> add one more segment to the path
                        # (need to draw doubled points for possibly "line join"
                        # user may have defined via overriding beginPath)
                        canvas.lineTo(nextXPx - grp.x0, nextYPx - grp.y0)

                # else lines are 0-width or transparent, so not rendered

            else:
                """
                * Explicitly oriented bandedness occurs only for vert or
                * horizontal bars. x,y coordinates are connected into
                * a path (as in a line chart), and then that path
                * is extended into a closed polygon by adding a
                * closing segment formed from an appropriate
                * section of an axis or baseline.
                *
                """

                """
                * Draw area interpolated between successive bars.
                *
                * Note that the "opposite" edge could be a point on an
                * x or y axis, or on the curve's baseline, depending
                * on the kind of bar chart involved: it's the edge
                * of the bar that is furthest from the x,y point.
                *
                """
                closeStrokeAndFill = False
                if False == self.horizontallyBanded:
                    if Double.NaN==(prevX)  or  Double.NaN==(prevY):
                        # 1st point, or 1st point after a break in the line
                        self.oppositeEdge = self.getEdgeOppositeVertically(
                                                pp, symbol, y, onY2)
                        canvas.beginPath()
                        canvas.moveTo(xPx - grp.x0, self.oppositeEdge - grp.y0)
                        canvas.lineTo(xPx - grp.x0, yPx - grp.y0)

                    if Double.NaN==(nextX)  or  Double.NaN==(nextY):
                        # last point, or last point before a break in the line
                        canvas.lineTo(xPx - grp.x0, self.oppositeEdge - grp.y0)
                        closeStrokeAndFill = True

                    else:
                        canvas.lineTo(nextXPx - grp.x0, nextYPx - grp.y0)


                else:

                    if Double.NaN==(prevX)  or  Double.NaN==(prevY):
                        # 1st point, or 1st point after a break in the line
                        self.oppositeEdge = self.getEdgeOppositeHorizontally(
                                            pp, symbol, x, onY2)
                        canvas.beginPath()
                        canvas.moveTo(self.oppositeEdge - grp.x0, yPx - grp.y0)
                        canvas.lineTo(xPx - grp.x0, yPx - grp.y0)

                    if Double.NaN==(nextX)  or  Double.NaN==(nextY):
                        # last point, or last point before a break in the line
                        canvas.lineTo(self.oppositeEdge - grp.x0, yPx - grp.y0)
                        closeStrokeAndFill = True

                    else:
                        canvas.lineTo(nextXPx - grp.x0, nextYPx - grp.y0)




                if closeStrokeAndFill:

                    canvas.closePath()
                    borderWidth = symbol.getBorderWidth()
                    # negative (external) border requires double-wide stroke
                    if (borderWidth >= 0):
                        lineWidth = borderWidth
                    else:
                        lineWidth = 2*abs(borderWidth)
                    borderColor = symbol.getBorderColor()
                    backgroundColor = symbol.getBackgroundColor()

                    """ XXX: Simply dropping the rendering as we do below does not
                    * exactly simulate the effect of transparent border/fill,
                    * specifically:
                    *
                    * <ol>
                    *   <li> Transparent internal border ==> the background
                    *          fill shines through the inner half of that border
                    *   <li> Transparent external border ==> Works OK
                    *   <li> Transparent fill w external border ==>
                    *           border extended internally to width
                    *   <li> Transparent fill w internal border ==> works OK
                    * </ol>
                    *
                    * GWTCanvas does not (?) provide a mechanism to "stroke
                    * transparent pixels", which is what I really needed. And
                    * emulating this, though possible via properly positioned
                    * inner/outter regions, etc. would have required a lot of effort
                    * to assure that sharply peaked angles, say, get rendered right.
                    *
                    """

                    # non-negative borders fill before stroking (thus
                    # stroke overwrites internal half of border)
                    if borderWidth >= 0  and  thickness > 0  and  GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and  "transparent" != backgroundColor:
                        canvas.setFillStyle(backgroundColor)
                        canvas.fill()


                    # stroke whenever a border is present
                    if borderWidth != 0  and  GChartConsts.TRANSPARENT_BORDER_COLOR != borderColor  and  "transparent" != borderColor:
                        canvas.setStrokeStyle(borderColor)
                        canvas.setLineWidth(lineWidth)
                        canvas.stroke()


                    # negative borders fill AFTER stroking (thus zapping
                    # the internal half of the stroked border).
                    if borderWidth < 0  and  thickness > 0  and  GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and  "transparent" != backgroundColor:
                        canvas.setFillStyle(backgroundColor)
                        canvas.fill()



         # if 0 == spacing  and  None != canvas  and  thickness > 0
        # next point defined
        # not a zero thickness connection
        elif (not Double.NaN==(nextX))  and  (not Double.NaN==(nextY))  and   thickness > 0  and    (x!=nextX  or  y!=nextY):
            # this/next point not overlayed
            if 0 == spacing:
                # 1px is as close as HTML-element
                spacing = 1;  # based filling can get to continuous

            d = self.distance(xPx,yPx,nextXPx,nextYPx)
            nChunks = int(round(d/spacing))
            if nChunks > 1:
                deltaX = nextXPx - xPx
                deltaY = nextYPx - yPx
                dXIsLonger = deltaX*deltaX > deltaY*deltaY
                if dXIsLonger:
                    deltaY /= deltaX; # from now on, dy is really dy/dx
                    deltaX /= nChunks;# from now on, dx is for 1 chunk

                else:
                    deltaX /= deltaY;  # from now on, dx is really dx/dy
                    deltaY /= nChunks; # from now on, dy is for 1 chunk

                # i==0 corresponds to the (to-be-drawn-last) symbol on (x,y).
                for i in range(1, nChunks):
                    # linearly interpolate forwards towards the next
                    # point; forward interpolation (usually) lets us
                    # place the "main" symbol for the original point on
                    # top of these interpolated symbols, in one pass.

                    # Rounding to the longer dimension first, then
                    # using that pixelated position to determine other
                    # dimension tends to keep points closer to being
                    # on the mathematically ideal line (at the cost of
                    # being less evenly spaced along that line). It's
                    # not too hard to see the improved alignment on
                    # GChartExample03, for example.
                    if dXIsLonger:
                        xi = round(xPx + deltaX * i)
                        yi = round(yPx + deltaY*(xi - xPx))

                    else:
                        # delta y is longer
                        yi = round(yPx + deltaY * i)
                        xi = round(xPx + deltaX*(yi - yPx))



                    # interpolated symbols set width & height to
                    # thickness, but are otherwise the same as main
                    # symbol at (x,y)
                    self.realizeOneImageOfSymbol(pp, grp, arp, symbol, None,
                                    onY2,
                                    clipPlotArea,
                                    clipDecoratedChart,
                                    xi, yi,
                                    prevXPx, prevYPx,
                                    nextXPx, nextYPx,
                                    thickness,
                                    thickness)


            # else points too close to require any "filler" elements

        # the "main" symbol (the one on the (x,y) point itself) is
        # rendered last to put it on top of interpolated images; this
        # is also where any annotation on the point gets rendered.
        if drawMainSymbol:
            self.realizeOneImageOfSymbol(pp, grp, arp, symbol, annotation,
                            onY2,
                            clipPlotArea,
                            clipDecoratedChart,
                            xPx, yPx,
                            prevXPx, prevYPx,
                            nextXPx, nextYPx,
                            symbol.getWidth(pp),
                            symbol.getHeight(pp,onY2))






 # end of class SymbolType



class HBarBaseline (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm, 0.5, 0.5, 0, 0,  True)

    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_HBAR_BASELINE_HOVER_LOCATION

    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return x - xMid


    def getUpperLeftX(self, width, x, xPrev, xNext, xMin, xMax, xMid, xMouse):
        return xMid



    def getIconHeight(self, legendFontSize):
        return int (round(legendFontSize/2.))

    def getIconWidth(self, legendFontSize):
        return legendFontSize


 # end of class HBarBaseline
class HBarLeft (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm, 0.5, 0.5, 0.5, 0.5,  True)

    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_HBARLEFT_HOVER_LOCATION

    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return x - xMin

    def getIconHeight(self, legendFontSize):
        return int (round(legendFontSize/2.))

    def getIconWidth(self, legendFontSize):
        return legendFontSize


 # end of class HBarLeft

class HBarRight (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm, 0.5, 0.5, 0.5, 0.5, True)


    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_HBARRIGHT_HOVER_LOCATION

    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return xMax - x

    def getIconHeight(self, legendFontSize):
        return int ( round(legendFontSize/2.))

    def getIconWidth(self, legendFontSize):
        return legendFontSize

 # end of class HBarRight


# draws a connected straight line between successive points
class LineSymbolType (SymbolType):
    def __init__(self):
        # same constructor as BOX_CENTER, which centers line segments on
        # the points that they represent, as required.
        SymbolType.__init__(self, 0, 0, 0, 0, 0, 0)


    # fillSpacing to use when a symbol's fillSpacing is
    # set to GChartConsts.NAI (an undefined integer)
    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_LINE_FILL_SPACING

    # fillThickness to use when a symbol's fillThickness is
    # set to GChartConsts.NAI (an undefined integer)
    def defaultFillThickness(self):
        return GChartConsts.DEFAULT_LINE_FILL_THICKNESS

    def getIconHeight(self, legendFontSize):
        return 3; # leaves room for a 1px border and a center

    def getIconWidth(self, legendFontSize):
        return max(3, legendFontSize)

    """
    * Draws an approximate line from x,y to nextX, nextY, using an
    * appropriate series of vertical (for a > 45 degree slope) or (for
    * a < 45 degree slope) horizontal line segments. If a GWT canvas
    * is available and if continuous fill (fillSpacing==0) was
    * requested the lineTo,stroke,etc. of the canvas Widget are
    * instead used to draw the line.
    * <p>
    *
    * The canvas part of this code assumes/requires that points
    * on a curve are rendered sequentially, and that on the
    * first point on the curve <tt>prevX</tt> and
    * <tt>prevY</tt>, and on the last point <tt>nextX</tt> and
    * <tt>nextY</tt>, are undefined (Double.NaN)
    *
    """

    def realizeSymbol(self, pp, grp, arp, symbol, annotation, onY2, clipPlotArea, clipDecoratedChart, drawMainSymbol, x, y, prevX, prevY, nextX, nextY):

        if (Double.NaN==(x))  or  (Double.NaN==(y)):
            # this point undefined (isNaN)
            return

        # else point itself is at least defined

        spacing = symbol.getFillSpacing()
        thickness = symbol.getFillThickness()
        canvas = grp.getCanvas()

        if 0 == spacing  and  None != canvas  and  thickness > 0:
            # when canvas is available and continuous fill requested,
            # BOX_CENTER and LINE work exactly the same way
            BOX_CENTER.realizeSymbol(
                    pp, grp, arp, symbol, annotation,
                    onY2,  clipPlotArea, clipDecoratedChart, drawMainSymbol,
                    x,  y, prevX,  prevY, nextX,  nextY)
            return


        xPx = pp.xToPixel(x)
        yPx = pp.yToPixel(y, onY2)
        nextXPx = pp.xToPixel(nextX)
        nextYPx = pp.yToPixel(nextY, onY2)

        # next point defined
        # not a zero thickness connection
        if (not Double.NaN==(nextX))  and  (not Double.NaN==(nextY))  and   thickness > 0  and    (x!=nextX  or  y!=nextY):
            # this/next point not overlayed
            # draw HTML-element rendered line segment

            # Continuous fill not supported; 1px is reasonable approx.
            if 0 == spacing:
                spacing = 1

            deltaX = nextXPx - xPx
            deltaY = nextYPx - yPx
            dXIsShorter = deltaX*deltaX < deltaY*deltaY
            # increasing width by 1 adds half px on each edge
            # to heal the occasional roundoff-induced gap
            EPS = 1
            # TODO: the case in which the connecting line does not intersect the
            # plot area, and off-plot-area points are not being drawn is handled
            # very inefficiently, and not entirely correctly, by trying to draw
            # the entire line and excluding each segment as we attempt to draw it.
            # Need to compute intersecting sub-line-segment and just draw that
            # instead, ignoring lines with no intersecting segments completely. Can
            # make a huge difference with lots of off-chart points, such as a
            # deliberately narrowed x axis range.
            if deltaX == 0:
                # special-case of vertical line

                self.realizeOneImageOfSymbol(pp, grp, arp, symbol, None,
                                        onY2,
                                        clipPlotArea,
                                        clipDecoratedChart,
                                        xPx,
                                        0.5*(yPx+nextYPx),
                                        Double.NaN, Double.NaN,
                                        nextXPx, nextYPx,
                                        thickness,
                                        abs(nextYPx - yPx)+EPS)

            elif deltaY == 0:
                # special case of horizontal line

                self.realizeOneImageOfSymbol(pp, grp, arp, symbol, None,
                                        onY2,
                                        clipPlotArea,
                                        clipDecoratedChart,
                                        0.5*(xPx+nextXPx),
                                        yPx,
                                        Double.NaN, Double.NaN,
                                        nextXPx, nextYPx,
                                        abs(nextXPx - xPx)+EPS,
                                        thickness)

            elif dXIsShorter:
                # series of vertical segments
                xMin = min(xPx, nextXPx)
                xMax = max(xPx, nextXPx)
                yAtXMin = min(xPx, nextXPx)
                yAtXMax = max(xPx, nextXPx)

                xiPrev = xMin
                yiPrev = yAtXMin
                xi = xiPrev
                yi = yiPrev
                # round up to err on side of providing more detail
                N = int (math.ceil((xMax-xMin)/spacing))
                dy = abs((yAtXMax - yAtXMin)/N)+EPS
                for i in range(1, N):
                    xi = xMin + i*(xMax - xMin)/N
                    yi = yAtXMin + i * (yAtXMax - yAtXMin)/N
                    self.realizeOneImageOfSymbol(pp, grp, arp, symbol, None,
                                            onY2,
                                            clipPlotArea,
                                            clipDecoratedChart,
                                            0.5*(xiPrev+xi), 0.5*(yiPrev+yi),
                                            Double.NaN, Double.NaN,
                                            nextXPx, nextYPx,
                                            thickness, dy)
                    xiPrev = xi
                    yiPrev = yi


            else:
                # dY is shorter. Series of horizontal segments
                yMin = min(yPx, nextYPx)
                yMax = max(yPx, nextYPx)
                xAtYMin = min(yPx, nextYPx)
                xAtYMax = max(yPx, nextYPx)

                xiPrev = xAtYMin
                yiPrev = yMin
                xi = xiPrev
                yi = yiPrev
                N = int (math.ceil((yMax-yMin)/spacing))
                dx = abs((xAtYMax - xAtYMin)/N)+ EPS
                for i in range(1, N):
                    yi = yMin + i*(yMax - yMin)/N
                    xi = xAtYMin + i * (xAtYMax - xAtYMin)/N
                    self.realizeOneImageOfSymbol(pp, grp, arp, symbol, None,
                                            onY2,
                                            clipPlotArea,
                                            clipDecoratedChart,
                                            0.5*(xiPrev+xi),0.5*(yiPrev+yi),
                                            Double.NaN, Double.NaN,
                                            nextXPx, nextYPx,
                                            dx, thickness)
                    xiPrev = xi
                    yiPrev = yi




        # the "main" symbol (the one on the (x,y) point itself) is
        # rendered last to put it on top of interpolated images
        if drawMainSymbol:
            w = symbol.getWidth(pp)
            h = symbol.getHeight(pp, onY2)
            self.realizeOneImageOfSymbol(pp, grp, arp, symbol, annotation,
                                    onY2,
                                    clipPlotArea,
                                    clipDecoratedChart,
                                    xPx, yPx,
                                    Double.NaN, Double.NaN,
                                    nextXPx, nextYPx,
                                    w, h)

     # realizeSymbol


""" Symbols that are assigned this symbol type can be used
* to represent a pie chart slice.
*
* The pivot point (center of containing pie) is at the x,y
* location of the point. Typically, only a single point
* per pie-slice curve is used (multiple points simply
* translate the same pie slice symbol to another position,
* such behavior is useful if you want to use
* a pie slice as a traditional curve symbol, but
* it isn't needed for a typical pie chart).
* <p>
*
* The initial angle and angle subtended by the slice are
* specified by the <tt>pieSliceOrientation</tt> and
* <tt>pieSliceSize</tt> properties of the host
* <tt>Symbol</tt> (these properties only have meaning with
* pie slice symbol types). Typically, several curves share
* a common pie center point (x,y) and have orientations
* and sizes that are coordinated so that the slices fit
* together to form a single complete pie. GChart
* facilitates this by choosing (by default) the next
* slice's orientation so that it is adjacent to the
* preceeding slice. However, other useful idioms include,
* for example, adjusting the x,y pivots to produce
* "exploded pie charts", or using a single slice that
* fills up the entire pie as a disc-like alterto
* <tt>BOX_CENTER</tt>.  <p>
*
* The radius of the slice is chosen as the radius such
* that the rectangle defined by the hosting Symbol's width
* and height just barely fits within a circle with that
* radius. This convention allows users to define the
* pie radius in terms of the x model coordinates, y model
* coordinates, or in pixels, as desired.
* <p>
*
* The host <tt>Symbol</tt>'s fillSpacing and fillThickness
* properties, along with horizontallyShaded and
* verticallyShaded properties of this SymbolType, govern
* how the slice is filled in.
*
* For more information with example code, see the
* discussion under the {@link #PIE_SLICE_OPTIMAL_SHADING
* PIE_SLICE_OPTIMAL_SHADING} symbol type.
*
"""

# min/max x (cosine) and y (sine) over "unit circle slice"
class SliceLimits(object):
    pass

class PieSliceSymbolType (SymbolType):

    def __init__(self, horizontallyShaded, verticallyShaded, optimallyShaded, pixelPadLeft, pixelPadRight, pixelPadTop, pixelPadBottom):
        # same as BOX_SOUTHEAST (allows shading bars to be
        # easily positions by their upper left corners):
        SymbolType.__init__(self, 1,1, pixelPadLeft, pixelPadRight,
                pixelPadTop, pixelPadBottom)

        self.horizontallyShaded = horizontallyShaded
        self.verticallyShaded = verticallyShaded
        self.optimallyShaded = optimallyShaded


    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_PIE_SLICE_HOVER_LOCATION

    """
    * @Override
    *
    * For simplicity, pie slices are given the upper bound
    * band thickness of a slice that occupies the entire pie.
    * <p>
    *
    * The case where hit test banding is most needed: lots
    * of very small full pies on a single curve (pie used as
    * circular alterto a rectangular point marker)
    * won't suffer from this up-sizing approximation,
    * since it uses full pies anyway.
    *
    """
    def getBandThickness(self, pp, sym, onY2):
        result = max(MIN_BAND_SIZE,
        2*sym.getPieSliceRadius(pp, onY2))
        return result

    """
    * @override
    *
    * Pie slices use a special radially oriented brush, whose radial
    * dimension is the larger of the specified brush width and
    * height.
    * <p>
    *
    * So, from the point of view of the banded/binned hit testing
    * algorithm, which works entirely with rectangles, it is as if
    * the brush were a square with side equal to the larger of the
    * brush width and height. Thus, regardless of if the pie uses
    * horizontal or vertical hit test banding, the as-if-rectangular
    * brush used in binned/banded hit testing is same square box,
    * given by this method and its companion, <tt>getBrushWidth</tt>,
    * below.
    * <p>
    *
    * This code also relies on the fact that for pie slices, only the
    * larger of width, height has an impact on the more exact,
    * slice/angle/radius closeness testing that is applied only to
    * the subset of nearby points determined by using the bins/bands.
    * So, making brush width and height the same for pie slices
    * doesn't cause any detail hit testing errors (as it would for ordinary
    * rectangular hit testing).
    * <p>
    *
    * TODO: Above works (I think) but is convoluted. Try to find a
    * clearer, simpler, way to express/handle pie slice differences.
    * The special case brush location handling for pies also seems
    * a bit obscure.
    *
    """
    def getBrushHeight(self, sym):
        result = max(sym.getBrushHeight(),
        sym.getBrushWidth())
        return result

    # @override (pie slices always use a centered location)
    def getBrushLocation(self, sym):
        result = AnnotationLocation.CENTER
        return result

    # @override (see comment on getBrushHeight above)
    def getBrushWidth(self, sym):
        result = max(sym.getBrushHeight(),
        sym.getBrushWidth())
        return result



    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_PIE_SLICE_FILL_SPACING

    def defaultFillThickness(self):
        return GChartConsts.DEFAULT_PIE_SLICE_FILL_THICKNESS

    def defaultHovertextTemplate(self):
        return GChartConsts.DEFAULT_PIE_SLICE_HOVERTEXT_TEMPLATE


    # Gets min/max sin, cos over slice cut from unit circle
    def getSliceLimits(self, tMin, tMax):
        result = SliceLimits()
        xMin = 0; # origin of 0,0 present in every slice
        xMax = 0; # (it's the pie center/slice pivot point)
        yMin = 0
        yMax = 0
        tmp = 0
        # points where each edge intersects the arc could be
        # extremal points--include them too.
        tmp = math.cos(tMin)
        xMin = min(xMin , tmp)
        xMax = max(xMax , tmp)
        tmp = math.sin(tMin)
        yMin = min(yMin , tmp)
        yMax = max(yMax , tmp)

        tmp = math.cos(tMax)
        xMin = min(xMin , tmp)
        xMax = max(xMax , tmp)
        tmp = math.sin(tMax)
        yMin = min(yMin , tmp)
        yMax = max(yMax , tmp)

        # finally if slice includes any special extreme points
        # on the arc (namely, points of the arc that are
        # either due north, due south, due east or due west)
        # include those points in determining the min/max x
        # and min/max y included in the slice:
        halfPi = math.pi/2.
        i = int (math.ceil(tMin/halfPi))
        while i*halfPi < tMax:
            t = i*halfPi
            tmp =  math.cos(t)
            xMin = min(xMin , tmp)
            xMax = max(xMax , tmp)
            tmp = math.sin(t)
            yMin = min(yMin , tmp)
            yMax = max(yMax , tmp)
            i += 1

        result.xMin = xMin
        result.xMax = xMax
        result.yMin = yMin
        result.yMax = yMax

        return result



    def getEdgeLeft(self, pp, symbol, x, onY2):

        r = symbol.getPieSliceRadius(pp, onY2)
        theta0 = symbol.getPieSliceTheta0()
        theta1 = symbol.getPieSliceTheta1()
        sl = self.getSliceLimits(theta1, theta0)
        xPx = pp.xToPixel(x)
        # scale up the xMin on unit circle to get to left edge
        result =  xPx + sl.xMin * r
        return result

    def getEdgeRight(self, pp, symbol, x, onY2):
        r = symbol.getPieSliceRadius(pp, onY2)
        theta0 = symbol.getPieSliceTheta0()
        theta1 = symbol.getPieSliceTheta1()
        sl = self.getSliceLimits(theta1, theta0)
        xPx = pp.xToPixel(x)
        # scale up the xMax on unit circle to get to right edge
        result = xPx + sl.xMax * r
        return result



    def getEdgeTop(self, pp, symbol, y, onY2):

        r = symbol.getPieSliceRadius(pp, onY2)
        theta0 = symbol.getPieSliceTheta0()
        theta1 = symbol.getPieSliceTheta1()
        sl = self.getSliceLimits(theta1, theta0)
        yPx = pp.yToPixel(y, onY2)
        # minus for the Cartesian to pixel-coord transform
        result = yPx - sl.yMax * r
        return result

    def getEdgeBottom(self, pp, symbol, y, onY2):

        r = symbol.getPieSliceRadius(pp, onY2)
        theta0 = symbol.getPieSliceTheta0()
        theta1 = symbol.getPieSliceTheta1()
        sl = self.getSliceLimits(theta1, theta0)
        yPx = pp.yToPixel(y, onY2)
        # minus for the Cartesian to pixel-coord transform
        result = yPx - sl.yMin * r
        return result




    # returns the y coordinate where a pie slice edge
    # intersects a given vertical line, or NaN if none.
    def yWherePieEdgeIntersectsVerticalLine(self, xOfVerticalLine, xPieCenter, yPieCenter, pieRadius, pieEdgeAngle):
        result = Double.NaN
        dxToArc = pieRadius*math.cos(pieEdgeAngle)
        if dxToArc != 0:
            # The fraction of the way (from pie center to pie perimeter
            # along the pie slice edge) that you must go to reach the point
            # at which the vertical line intersects with the pie slice
            # edge. For example, this fraction is 0.5 whenever the vertical
            # line bisects the pie slice edge.
            t = (xOfVerticalLine-xPieCenter)/dxToArc
            if GChartUtil.withinRange(t,0,1):
                result = yPieCenter - t * pieRadius * math.sin(pieEdgeAngle)

        return result


    # returns the x coordinate where a pie slice edge
    # intersects a given horizontal line, or NaN if none.
    def xWherePieEdgeIntersectsHorizontalLine(self, yOfHorizontalLine,
                                             xPieCenter, yPieCenter, 
                                             pieRadius, pieEdgeAngle):
        result = Double.NaN
        dyToArc = pieRadius*math.sin(pieEdgeAngle)
        if dyToArc != 0:
            # The fraction of the way (from pie center to pie perimeter
            # along the pie slice edge) that you must go to reach the point
            # at which the horizontal line intersects with the pie slice
            # edge. For example, this fraction is 0.5 whenever the horizontal
            # line bisects the pie slice edge.
            t = (yPieCenter - yOfHorizontalLine)/dyToArc
            if GChartUtil.withinRange(t,0,1):
                result = xPieCenter + t * pieRadius * math.cos(pieEdgeAngle)

        return result

    """
    * Returns the angle of a line extending from (0,0) to
    * (x,y) in radians in the standard range, 0 to 2*Pi. For
    * example, a line pointing due east such as (1,0) would
    * return 0, one pointing due north such as (0,0.5) would
    * return Pi/2, one pointing due west such as (-4.13,0)
    * would return Pi and the point (1,1) returns Pi/4.
    * <p>
    *
    * x,y are in the ordinary cartesian coordinate system
    * (not in the typical graphics/pixel coordinates)
    *
    """
    def angle(self, x, y):
        result = Double.NaN
        if x == 0:
            if y > 0:
                result = math.pi/2.

            elif y < 0:
                result = 3*math.pi/2.


        elif x> 0  and  y >= 0:
            result = math.atan(y/x)

        elif x<0  and  y >= 0:
            result = math.pi - math.atan(-y/x)

        elif x <0  and  y < 0:
            result = math.pi + math.atan(y/x)

        elif x > 0  and  y < 0:
            result = 2*math.pi- math.atan(-y/x)


        return result


    # is the given angle between the two angles given?
    def angleInRange(self, angle, theta0, theta1):

        if theta0 > theta1:
            return self.angleInRange(angle, theta1, theta0)

        # angle is in standard 0 to 2*Pi range, but thetas
        # can be "wrapped around" several negative
        # multiples of 2*Pi less than the standard range
        # this loop brings angle into same range as thetas
        while angle > theta1:
            angle -= 2*math.pi


        result = GChartUtil.withinRange(angle, theta0, theta1)
        return result


    """
    *
    * @Override
    *
    * The x, y coordinates at the "center" of the slice for
    * hit testing purposes.
    *
    * During hit testing, if more than one symbol touches
    * the brush, the point whose center is closest to
    * the mouse position is selected.
    *
    * To simplify the calculation, that center point is taken
    * to be the center of the pie containing the slice, rather
    * than the center of the slice per se. Though not an ideal
    * choice, it is unlikely to cause significant deviations
    * from user expectations, given how pie slices tend to be
    * used to compose full pies out of a series of
    * non-overlapping slices.
    *
    """
    def getCenterX(self, pp, symbol, iPoint):
        p = symbol.getParent().getPoint(iPoint)
        result = pp.xToPixel(p.getX())
        return result

    """ @Override
    *
    * See comment on getCenterX above.
    *
    """
    def getCenterY(self, pp, symbol, iPoint, onY2):
        p = symbol.getParent().getPoint(iPoint)
        result = pp.yToPixel(p.getY(), onY2)
        return result

    """
    * @Override
    *
    * Pie slices redefine what constitutes intersection of the
    * mouse-centered brush and the rendered symbol to be:
    * "mouse position within a radially-expanded
    * version of the slice". The pie radius is expanded by
    * half the larger dimension of the point selection brush.
    *
    """
    def isIntersecting(self, pp, symbol, iPoint, onY2, xBrush, yBrush,
                             brushWidth, brushHeight):

        result = False
        p = symbol.getParent().getPoint(iPoint)
        x = p.getX();  # pie center point (slice pivot)
        y = p.getY()
        xPx = pp.xToPixel(x)
        yPx = pp.yToPixel(y, onY2)
        dx = xBrush-xPx
        # - represents switch from graphics to cartesian coordinates
        dy = -(yBrush-yPx)

        rSquared = dx*dx + dy*dy
        angle = self.angle(dx, dy)
        # pie angles grow clockwise but radians counter-clockwise,
        # hence the odd "0 into max, 1 into min" mapping below.
        thetaMax = symbol.getPieSliceTheta0()
        thetaMin = symbol.getPieSliceTheta1()
        rPiePlus = (symbol.getPieSliceRadius(pp, onY2) +
                        0.5*max(brushWidth, brushHeight))

        """
        * Enforce a minimum slice angle for hit testing
        * purposes, equivalent to  +/- 1 px of play along the
        * arcs of tiny slices, to make them easier to select:<p>
        *
        * <pre>
        *   r*minDTheta = 1 px
        * </pre>
        *
        * This helps with tiny slices adjacent to large ones, but if
        * several tiny slices are adjacent to each other, or if both
        * adjacent slices come after the tiny slice in the curve
        * order (e.g. the tiny slice is the very first slice) it
        * still won't be selectable. Developers can switch
        * curve order to get around this, but it's not ideal.
        * <p>
        *
        * TODO: Integrate a "closest to slice angle" criterion
        * to resolve ties when hit testing slices to provide
        * a better hit testing behavior with small or overlapping
        * slices.
        *
        """
        minDTheta = (rPiePlus < 1) and 1.0 or 1./rPiePlus
        if thetaMax - thetaMin < 2*minDTheta:
            thetaMid = 0.5*(thetaMax + thetaMin)
            thetaMin = thetaMid - minDTheta
            thetaMax = thetaMid + minDTheta

        if rSquared <= rPiePlus*rPiePlus  and  self.angleInRange(angle,thetaMin,thetaMax):
            result = True


        return result



    def realizeSymbol(self, pp, grp, arp, symbol, annotation, onY2, clipPlotArea, clipDecoratedChart, drawMainSymbol, x, y, prevX, prevY, nextX, nextY):

        if not drawMainSymbol:
            return

        xPx = pp.xToPixel(x)
        yPx = pp.yToPixel(y, onY2)
        spacing = symbol.getFillSpacing()
        thickness = symbol.getFillThickness()
        r = symbol.getPieSliceRadius(pp, onY2)
        theta0 = symbol.getPieSliceTheta0()
        theta1 = symbol.getPieSliceTheta1()
        canvas = grp.getCanvas()
        if (Double.NaN==(xPx))  or  (Double.NaN==(yPx)):
            return; # undefined slice pivot point

        elif clipPlotArea  and  not self.intersects(xPx-r, yPx-r, xPx+r, yPx+r, 0, 0, pp.getXChartSize(), pp.getYChartSize()):
            return; # rect containing pie is off plot area

        elif clipDecoratedChart:
            yAxisWidth = pp.getYAxisEnsembleWidth()
            titleThickness = pp.chartTitleThickness()
            if not SymbolType.intersects(self, 0.0 - yAxisWidth,
                                         0.0 - titleThickness, 
                            pp.getXChartSizeDecoratedQuickly()-yAxisWidth, 
                            pp.getYChartSizeDecoratedQuickly()-titleThickness, 
                            xPx-r, yPx-r, xPx+r, yPx+r):
                return; # rect containing pie is off decorated chart


        # else bounding rectangle of pie containing the slice visible

        if 0 == spacing  and  None != canvas  and  thickness > 0:
            # continuous fill pie slice and canvas is available

            """
            * Solid fill pie slices implement the notion of internal vs
            * external borders a bit differently than rectangular
            * symbols.
            * <p>
            *
            * Internal borders are always drawn "centered",
            * that is, half internal, half external.  In part,
            * this is because that is how "stroke" of the
            * canvas API does it, so it's easier to implement.
            * But mainly it is because, when you assemble
            * several slices into a full pie, a centered
            * border, provided that each slice has the same
            * border color, is really the only choice that
            * looks right (this is a constraint of the
            * geometry how the slices fit together into a
            * pie).  <p>
            *
            * External borders (negative border width) are
            * drawn outside the slice proper by doubling the
            * thickness, and then over-filling the internal
            * part of the border by issuing the fill after,
            * instead of before, the border is drawn. Though
            * external borders don't look right within a pie
            * (because of how the slices occlude each other's
            * borders) they can be handy for making slice
            * selection borders that are drawn entirely
            * outside of the selected slice.
            *
            """
            borderWidth = symbol.getBorderWidth()
            if borderWidth >= 0:
                adjustedBorderWidth = borderWidth 
            else:
                adjustedBorderWidth = 2*abs(borderWidth)

            """
            * With incubator's <tt>GWTCanvas</tt>, IE7 & Chrome draw
            * 0 and 2*Pi slices incorrectly.  See issues #278
            * #282 for more information: <p>
            *
            * http:#code.google.com/p/google-web-toolkit-incubator/issues/detail?id=278
            * http:#code.google.com/p/google-web-toolkit-incubator/issues/detail?id=282
            * <p>
            *
            * Pies with > 1000 px radii are unlikely (tried
            * using 10000, but it didn't work in Chrome).
            *
            """
            MIN_DTHETA = 1./1000
            MAX_DTHETA = 2*math.pi - MIN_DTHETA

            # canvas measures angles clockwise from +x-axis
            # our angles are counter-clockwise from +x-axis
            dTheta = theta0 - theta1
            angleStart = 2*math.pi-theta0
            angleEnd = (angleStart +
                    max(MIN_DTHETA, min(dTheta, MAX_DTHETA)))

            if dTheta >= MIN_DTHETA  or  borderWidth < 0:
                canvas.beginPath()
                canvas.setLineWidth(adjustedBorderWidth)

                canvas.arc(xPx - grp.x0, yPx - grp.y0, r,
                            angleStart, angleEnd, False)
                if dTheta <= MAX_DTHETA:
                    canvas.lineTo(xPx - grp.x0, yPx- grp.y0)

                # else avoid "line to center" in full pies

                canvas.closePath()

                #canvas.translate(xPx - grp.x0, yPx - grp.y0)

                borderColor = symbol.getBorderColor()
                backgroundColor = symbol.getBackgroundColor()
                """
                * XXX: The approach to transparent border/fill
                * used below is to simply not stroke the border
                * or to not fill the inside of the path. This
                * isn't exactly right, because the region where
                * the border overlaps the filled area does not
                * always become transparent when it should.
                * These errors likely won't be noticed in most
                * usage scenarios, and without the ability to
                * replace filled/stroked regions with
                * transparent pixels (I don't think GWTCanvas
                * can do this?) there isn't an easy fix.
                *
                """

                # non-negative borders fill before stroking (thus
                # stroke overwrites internal half of border)
                # GWTCanvas thows an exception w "transparent"
                if (borderWidth >= 0  and  thickness > 0  and  
                    GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and  
                    "transparent" != backgroundColor):
                    canvas.setFillStyle(backgroundColor)
                    canvas.fill()


                # stroke whenever a border is present
                if (borderWidth != 0  and  
                    GChartConsts.TRANSPARENT_BORDER_COLOR != borderColor  and  
                    "transparent" != borderColor):
                    canvas.setStrokeStyle(borderColor)
                    canvas.stroke()


                # negative borders fill AFTER stroking (thus zapping
                # the internal half of the stroked border).
                if (borderWidth < 0  and  
                    thickness > 0  and  
                    GChartConsts.TRANSPARENT_BORDER_COLOR != backgroundColor  and  
                    "transparent" != backgroundColor):
                    canvas.setFillStyle(backgroundColor)
                    canvas.fill()

            # else 0-sized slice, 0 or internal border, is just dropped

        else:
            if 0 == spacing:
                spacing = 1

            # if center point is on the chart, draw it:

            prevXPx = pp.xToPixel(prevX)
            prevYPx = pp.yToPixel(prevY, onY2)
            nextXPx = pp.xToPixel(nextX)
            nextYPx = pp.yToPixel(nextY, onY2)
            nBands = int ( round(r/spacing) )
            """ Holds positions at which the current vertical or
            * horizontal "gridline-like band" intersects the outter
            * perimeter of the current pie slice. These positions
            * are used to define the location and size of shading
            * bars required for each pie slice.
            *
            * Note: Although most pie slice perimeters are convex
            * and thus have perimeters that intersect a gridline
            * in at most two points, pie slices that take up more
            * than half of the entire pie have perimeters that
            * can (across their pacman-like mouth) intersect a
            * gridline at up to four points.
            *
            """
            MAX_PIE_SLICE_PERIMETER_INTERSECTIONS = 4
            p = [0.0, 0.0, 0.0, 0.0]
            EPS = 0.5
            sl = self.getSliceLimits(theta1, theta0)
            optimalIsVertical = (sl.yMax - sl.yMin) > (sl.xMax - sl.xMin)
            isFullPie = (symbol.getPieSliceSize() == 1.0)
            # perform any vertical shading that may be required:
            if (nBands > 0  and  
                 (self.verticallyShaded  or  
                      (self.optimallyShaded  and  
                           optimalIsVertical))):
                for i in range(int(round(nBands*sl.xMin)),
                               int(sl.xMax*nBands)):
                    nP = 0
                    dxPx = r*(i+0.5)/nBands
                    dyPx = math.sqrt(r*r - dxPx*dxPx)
                    # x of vertical line bisecting the shading band
                    xi = xPx + dxPx
                    # y-positions where this band crosses circle perimeter
                    c1 = yPx - dyPx
                    c2 = yPx + dyPx
                    # y-positions where this band crosses each slice edge
                    # (full pies don't have pie slice edges)
                    if isFullPie:
                        e1 = Double.NaN
                    else:
                        e1 = self.yWherePieEdgeIntersectsVerticalLine(
                                            xi,xPx,yPx,r,theta0)
                    if isFullPie:
                        e2 = Double.NaN
                    else:
                        e2 = self.yWherePieEdgeIntersectsVerticalLine(
                                            xi,xPx,yPx,r,theta1)
                    # Exclude circle perimeter intercepts outside of
                    # the slice.  Note: Pixel y coordinates used in
                    # browser increase going down, but cartesian y
                    # coordinates used in trig functions increase
                    # going up, hence the sign-flipping on second arg
                    # of angle function below.
                    if self.angleInRange(self.angle(xi-xPx,yPx-c1),theta0,theta1):
                        p[nP] = c1
                        nP += 1

                    # intersection points sorted by increasing y within p[]
                    if e1 < e2:
                        if not Double.NaN==(e1):
                            p[nP] = e1
                            nP += 1

                        if not Double.NaN==(e2):
                            p[nP] = e2
                            nP += 1


                    else:
                        if not Double.NaN==(e2):
                            p[nP] = e2
                            nP += 1

                        if not Double.NaN==(e1):
                            p[nP] = e1
                            nP += 1



                    if self.angleInRange(self.angle(xi-xPx, yPx-c2),theta0,theta1):
                        p[nP] = c2
                        nP += 1

                    for j in range(1, nP):
                        # logic below avoids drawing a line across the
                        # non-convex "pacman mouth" that occurs with any
                        # bigger-than-half-pie-sized slices, by
                        # requiring that a line drawn from the pie
                        # center to an interpolated point on each
                        # shading bar forms an angle in the slice's
                        # angular range. We use a point 30% rather than
                        # 50% of the way inbetween to avoid ever hitting the
                        # center of the pie (where angle is ambiguous).
                        #
                        # Note that, due to roundoff error, you cannot
                        # ALWAYS rely on the (mathematically correct)
                        # fact that problematic bars always connect p[1]
                        # and p[2].
                        if (abs(theta0-theta1) <= math.pi  or  
                            self.angleInRange(self.angle(xi-xPx,
                                                         yPx-(0.3*p[j]+0.7*p[j-1])),
                                              theta0,theta1)):
                            # widening of EPS pixels on either side fills in
                            # tiny intra-slice gaps (that can otherwise appear
                            # due to roundoff) by making each bar a tad bigger.
                            self.realizeOneImageOfSymbol(pp, grp, arp,
                                                    symbol, None,
                                                    onY2,
                                                    clipPlotArea,
                                                    clipDecoratedChart,
                                                    xi-0.5*
                                                    thickness,
                                                    p[j-1]-EPS,
                                                    prevXPx, prevYPx,
                                                    nextXPx, nextYPx,
                                                    thickness,
                                                    p[j] - p[j-1] +2*EPS)





            # Now do any required horizontal shading. This is
            # basically the same as the code for vertical shading
            # above (w appropriate transposition/adjustments).
            if (nBands > 0  and  (self.horizontallyShaded  or  
                    (self.optimallyShaded  and  
                     not optimalIsVertical))):
                for i in range( int ( round(-nBands*sl.yMax)),
                                int ( -nBands * sl.yMin) ):
                    nP = 0
                    dyPx = r*(i+0.5)/nBands
                    dxPx = math.sqrt(r*r - dyPx*dyPx)
                    # y of the horizontal line bisecting the shading band
                    yi = yPx + dyPx

                    # x-positions where this band crosses circle perimeter
                    c1 = xPx - dxPx
                    c2 = xPx + dxPx

                    # x-positions where this band crosses each slice edge
                    # (full pies don't have pie slice edges)
                    if isFullPie:
                        e1 = Double.NaN
                        e2 = Double.NaN
                    else:
                        e1 = self.xWherePieEdgeIntersectsHorizontalLine(
                                yi,xPx,yPx,r,theta0)
                        e2 = self.xWherePieEdgeIntersectsHorizontalLine(
                                yi,xPx,yPx,r,theta1)
                    # exclude circle perimeter intercepts outside of
                    # the slice
                    if self.angleInRange(self.angle(c1-xPx, yPx-yi),theta0,theta1):
                        p[nP] = c1
                        nP += 1


                    # intersection points sorted by increasing x within p[]
                    if e1 < e2:
                        if not Double.NaN==(e1):
                            p[nP] = e1
                            nP += 1

                        if not Double.NaN==(e2):
                            p[nP] = e2
                            nP += 1


                    else:
                        if not Double.NaN==(e2):
                            p[nP] = e2
                            nP += 1

                        if not Double.NaN==(e1):
                            p[nP] = e1
                            nP += 1



                    if self.angleInRange(self.angle(c2-xPx, yPx-yi),theta0,theta1):
                        p[nP] = c2
                        nP += 1


                    for j in range(1, nP):
                        # c.f. comment on corresponding vertical code above.
                        if abs(theta0-theta1) <= math.pi  or  self.angleInRange(self.angle((0.3*p[j]+0.7*p[j-1])-xPx, yPx-yi), theta0,theta1):
                            # widening of EPS pixels on either side fills in
                            # tiny intra-slice gaps that can sometimes appear
                            # by making slices just a tad bigger.
                            self.realizeOneImageOfSymbol(pp, grp, arp,
                                                    symbol, None,
                                                    onY2,
                                                    clipPlotArea,
                                                    clipDecoratedChart,
                                                    p[j-1]-EPS,
                                                    yi-0.5*
                                                    thickness,
                                                    prevXPx, prevYPx,
                                                    nextXPx, nextYPx,
                                                    p[j]-p[j-1] + 2*EPS,
                                                    thickness)






        # if the image has an attached label, realize that
        if annotation!=None  and  (annotation.getText() is not None  or  annotation.getWidget() is not None)  and  annotation.getVisible():

            # plus x-axis, for shifts, always corresponds to
            # outward pointing radius that bisects the slice,
            # with positive y axis, for shifts, at a 90 degree
            # counter-clockwise rotation from this x. Basic
            # trigonometry and this spec yeilds lines below.
            thetaMid = (theta0+theta1)/2.
            dX = annotation.getXShift()
            dY = annotation.getYShift()
            sinTheta = math.sin(thetaMid)
            cosTheta = math.cos(thetaMid)
            loc = annotation.getLocation()
            if None == loc:
                loc = self.defaultAnnotationLocation()

            # note: pixel Y increases down but yShift & "trig Y"
            # increase going up, which explains dY sign reversal
            arp.renderAnnotation(annotation,
                                loc.decodePieLocation(thetaMid),
                                xPx+(r+dX)*cosTheta - dY*sinTheta,
                                yPx-(r+dX)*sinTheta - dY*cosTheta,
                                0, 0,
                                symbol)


 # end of class PieSliceSymbolType



class VBarBottom (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm,0.5,0.5,0.5,0.5, False)

    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_VBARBOTTOM_HOVER_LOCATION

    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return yMax - y

    def getIconHeight(self, legendFontSize):
        return legendFontSize

    def getIconWidth(self, legendFontSize):
        return int (round(legendFontSize/2.) )

 # end of class VBarBottom
class VBarBaseline (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm, 0, 0, 0.5, 0.5, False)

    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_VBAR_BASELINE_HOVER_LOCATION

    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return y - yMid


    def getUpperLeftY(self, height, y, yPrev, yNext, yMin, yMax, yMid, yMouse):
        return yMid


    def getIconHeight(self, legendFontSize):
        return legendFontSize

    def getIconWidth(self, legendFontSize):
        return int (round(legendFontSize/2.) )

 # end of class VBarBaseline
"""* Use vertical bars that extend from the top of the chart
** to each point on the curve.
*"""
class VBarTop (SymbolType):
    def __init__(self, wm, hm):
        SymbolType.__init__(self, wm, hm, 0.5, 0.5, 0.5, 0.5, False)

    def defaultFillSpacing(self):
        return GChartConsts.DEFAULT_BAR_FILL_SPACING

    def defaultHoverLocation(self):
        return GChartConsts.DEFAULT_VBARTOP_HOVER_LOCATION

    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return y - yMin

    def getIconHeight(self, legendFontSize):
        return legendFontSize

    def getIconWidth(self, legendFontSize):
        return int ( round(legendFontSize/2.))

 # end of class VBarTop

class AnnotationAnchor (SymbolType):
    #AnnotationLocation location
    def __init__(self, location):
        SymbolType.__init__(self, 0, 0, 0, 0, 0, 0)
        self.location = location

    # actual curve symbol zero-sized so it does not
    # appear--it's just for positioning the annotation.
    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return 0

    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return 0


    # Just return one of the standard 9 positions, or the mouse
    # coordinates, based on the location defined in the
    # constructor.
    def getUpperLeftX(self, width, x, xPrev, xNext, xMin, xMax, xMid, xMouse):
        if AnnotationLocation.AT_THE_MOUSE == self.location:
            if (GChartConsts.NAI == xMouse):
                result = Double.NaN
            else:
                result = xMouse

        elif AnnotationLocation.AT_THE_MOUSE_SNAP_TO_X == self.location:
            if (GChartConsts.NAI == xMouse):
                result = Double.NaN
            else:
                result = x

        elif AnnotationLocation.AT_THE_MOUSE_SNAP_TO_Y == self.location:
            if (GChartConsts.NAI == xMouse):
                result = Double.NaN
            else:
                result = xMouse

        elif AnnotationLocation.NORTHWEST == self.location  or  AnnotationLocation.WEST == self.location  or  AnnotationLocation.SOUTHWEST == self.location:
            result = xMin

        elif AnnotationLocation.NORTHEAST == self.location  or  AnnotationLocation.EAST == self.location  or  AnnotationLocation.SOUTHEAST == self.location:
            result = xMax

        else:
            # NORTH, CENTER, or SOUTH
            result = (xMin + xMax)/2


        return result


    def getUpperLeftY(self, height, y, yPrev, yNext, yMin, yMax, yMid, yMouse):
        if AnnotationLocation.AT_THE_MOUSE == self.location:
            if (GChartConsts.NAI == yMouse):
                result = Double.NaN
            else:
                result = yMouse

        elif AnnotationLocation.AT_THE_MOUSE_SNAP_TO_X == self.location:
            if (GChartConsts.NAI == yMouse):
                result = Double.NaN
            else:
                result = yMouse

        elif AnnotationLocation.AT_THE_MOUSE_SNAP_TO_Y == self.location:
            if (GChartConsts.NAI == yMouse):
                result = Double.NaN
            else:
                result = y

        elif AnnotationLocation.NORTHWEST == self.location  or  AnnotationLocation.NORTH == self.location  or  AnnotationLocation.NORTHEAST == self.location:
            result = yMin

        elif AnnotationLocation.SOUTHWEST == self.location  or  AnnotationLocation.SOUTH == self.location  or  AnnotationLocation.SOUTHEAST == self.location:
            result = yMax

        else:
            # WEST, CENTER, or EAST
            result = (yMin + yMax)/2

        return result



"""
* This symbol type provides a convenient anchor point at
* one of the standard 9 named positions within the plot
* area.  The actual x,y of the points using this symbol
* type is ignored.  Useful for placing annotations around
* and along the perimeter of the plot panel.<p>
*
* For example, chart decorations such as axis labels and
* footnotes internally use symbols of this type (with
* appropriate setAnnotationXShift or setAnnotationYShift
* adjustments to position the decoration appropriately
* relative to the anchor point). End-users can use a curve
* with this symbol type, along with a single point and
* appropriate widget-based annotation, to place a table in
* the upper left corner of the plot area, etc.
*
"""

"""*
** Points on curves with this symbol type are positioned
** at the center of the plot area, and do not have a
** visible symbol.<p>
**
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the center of the plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_CENTER = AnnotationAnchor(AnnotationLocation.CENTER)

"""*
** Points on curves with this symbol type are positioned
** at the center of the right edge of the plot area, and
** do not have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the center of the right
** edge of the plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_EAST = AnnotationAnchor(AnnotationLocation.EAST)

"""*
** When passed to the <tt>setHoverAnnotationSymbolType</tt>
** method, this symbol type enables
** <tt>setTitle</tt>-like, "anchored at the mouse cursor"
** hover annotation positioning. Specifically, hover annotions act as
** if they were annotations of 1px x 1px
** points placed at the current mouse cursor position.
** <p>
**
** Because this and its related symbol types,
** <tt>ANCHOR_MOUSE_SNAP_TO_X</tt> and
** <tt>ANCHOR_MOUSE_SNAP_TO_Y</tt>, are intended only to
** facilitate positioning of hover-induced pop-up annotations
** (via the <tt>setHoverAnnotationSymbolType</tt> method) I
** cannot imagine a scenario where it would make sense to use
** them as the symbol type of an ordinary, user defined, curve
** (if you find a use for this, please let me know).
**
**
** @see #ANCHOR_MOUSE_SNAP_TO_X ANCHOR_MOUSE_SNAP_TO_X
** @see #ANCHOR_MOUSE_SNAP_TO_Y ANCHOR_MOUSE_SNAP_TO_Y
** @see Symbol#setHoverLocation setHoverLocation
** @see Symbol#setHoverAnnotationSymbolType setHoverAnnotationSymbolType
** @see Symbol#setHovertextTemplate setHovertextTemplate
** @see Symbol#setHoverXShift setHoverXShift
** @see Symbol#setHoverYShift setHoverYShift
** @see Symbol#setHoverWidget setHoverWidget
*"""
ANCHOR_MOUSE = AnnotationAnchor( AnnotationLocation.AT_THE_MOUSE)

"""*
* The same as the ANCHOR_MOUSE symbol type, except that
* the x coordinate of the rendered symbol is taken from
* the x coordinate of the point, rather than the x
* coordinate of the mouse.
*
* @see #ANCHOR_MOUSE ANCHOR_MOUSE
* @see #ANCHOR_MOUSE_SNAP_TO_Y ANCHOR_MOUSE_SNAP_TO_Y
*
"""
ANCHOR_MOUSE_SNAP_TO_X = AnnotationAnchor(AnnotationLocation.AT_THE_MOUSE_SNAP_TO_X)
"""*
* The same as the ANCHOR_MOUSE symbol type, except that
* the y coordinate of the rendered symbol is taken from
* the y coordinate of the point, rather than the y
* coordinate of the mouse.
*
* @see #ANCHOR_MOUSE ANCHOR_MOUSE
* @see #ANCHOR_MOUSE_SNAP_TO_X ANCHOR_MOUSE_SNAP_TO_X
*
"""
ANCHOR_MOUSE_SNAP_TO_Y = AnnotationAnchor(AnnotationLocation.AT_THE_MOUSE_SNAP_TO_Y)
"""*
** Points on curves with this symbol type are positioned
** at the center of the top edge of the plot area, and do
** not have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the center of the top edge of
** the plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_NORTH = AnnotationAnchor(AnnotationLocation.NORTH)
"""*
** Points on curves with this symbol type are positioned
** at the upper right corner of the plot area, and do not
** have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the upper right corner of the
** plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_NORTHEAST = AnnotationAnchor(AnnotationLocation.NORTHEAST)

"""*
** Points on curves with this symbol type are positioned
** at the upper left corner of the plot area, and do not
** have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the upper left corner of the
** plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_NORTHWEST = AnnotationAnchor(AnnotationLocation.NORTHWEST)

"""*
** Points on curves with this symbol type are positioned
** at the center of the bottom edge of the plot area, and
** do not have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the center of the bottom edge
** of the plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_SOUTH = AnnotationAnchor(AnnotationLocation.SOUTH)


"""*
** Points on curves with this symbol type are positioned
** at the lower right corner of the plot area, and do not
** have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the lower right corner of the
** plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_SOUTHEAST = AnnotationAnchor(AnnotationLocation.SOUTHEAST)


"""*
** Points on curves with this symbol type are positioned
** at the lower left corner of the plot area, and do not
** have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the lower left corner of the
** plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_SOUTHWEST = AnnotationAnchor(AnnotationLocation.SOUTHWEST)

"""*
** Points on curves with this symbol type are positioned
** at the center of the left edge of the plot area, and do
** not have a visible symbol.<p>
**
** Use this symbol type, along with the
** <tt>setAnnotationLocation</tt>, <tt>setAnnotationXShift</tt> and
** <tt>setAnnotationYShift</tt> methods, to position
** annotations relative to the center of the left edge of
** the plot area.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see Curve.Point#setAnnotationYShift setAnnotationYShift
**
*"""
ANCHOR_WEST = AnnotationAnchor(AnnotationLocation.WEST)

"""* Use rectangles horizontally and vertically centered
** on each point of the curve """
BOX_CENTER = SymbolType(0,0,0,0,0,0)
"""* Use rectangles just to the right of, and
** vertically centered on, each point of the curve """
BOX_EAST = SymbolType(1, 0, 0.5, -0.5, 0, 0)
"""* Use rectangles just above, and horizontally centered
** on, each point of the curve """
BOX_NORTH = SymbolType(0, -1,0,0,-0.5,0.5)

"""* Use rectangles just above, and to the right of,
** each point of the curve """
BOX_NORTHEAST = SymbolType(1, -1, 0.5,-0.5,-0.5,0.5)

"""* Use rectangles just above and to the left of,
** each point of the curve """
BOX_NORTHWEST = SymbolType(-1, -1, -0.5, 0.5, -0.5, 0.5)

"""* Use rectangles just below, and horizontally centered
** on, each point of the curve """
BOX_SOUTH = SymbolType(0, 1, 0, 0, 0.5, -0.5)

"""* Use rectangles just below, and to the right of,
** each point of the curve """
BOX_SOUTHEAST = SymbolType(1, 1, 0.5, -0.5, 0.5, -0.5)

"""* Use rectangles just below, and to the left of,
** each point of the curve """
BOX_SOUTHWEST = SymbolType(-1, 1, -0.5, 0.5, 0.5, -0.5)

"""* Use rectangles just to the left of, and vertically centered
** on, each point of the curve """
BOX_WEST = SymbolType(-1, 0, -0.5, 0.5, 0, 0)
"""*
** Use horizontal bars that extend from the x,y position
** associated with each point, to the x position defined
** by the host <tt>Symbol</tt>'s baseline property, and that are
** vertically centered on the data point.
**
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
** @see Symbol Symbol
**
*"""
HBAR_BASELINE_CENTER = HBarBaseline(0,0)
"""*
** Use horizontal bars that extend from the x,y position
** associated with each point, to the x position defined
** by the host <tt>Symbol</tt>'s baseline property, and whose
** bottom edge passes through the data point.
**
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
** @see Symbol Symbol
**
*"""
HBAR_BASELINE_NORTH = HBarBaseline(0,-1)
"""*
** Use horizontal bars that extend from the x,y position
** associated with each point, to the x position defined
** by the host <tt>Symbol</tt>'s baseline property, and whose
** top edge passes through the data point.
**
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
**
*"""
HBAR_BASELINE_SOUTH = HBarBaseline(0,1)
"""* Use horizontal bars that extend from the right y-axis
** to each point on the curve, and that are vertically
** centered on the point.
*"""
HBAR_EAST = HBarRight(1,0)
line  = LineSymbolType()
"""*
** @deprecated
**
** As of version 2.4, this symbol has been redefined to
** be synonomous with the LINE symbol type.
** <p>
**
** Prior to v2.4, this symbol drew a horizontal bar from
** each point to the x coordinate of the next point.  Some
** applications may need to use a revised point set in
** order to produce the same curves using <tt>LINE</tt>
** that they used to produce with this symbol.  <p>
**
** See the discussion within the {@link #VBAR_NEXT
** VBAR_NEXT} symbol for more information about why
** support for these vertically and horizontally constrained
** connecting line symbol types was dropped.
**
** @see #LINE LINE
** @see #HBAR_PREV HBAR_PREV
** @see #VBAR_PREV VBAR_PREV
** @see #VBAR_NEXT VBAR_NEXT
**
*"""
HBAR_NEXT = line
"""* Use horizontal bars that extend from the right y-axis
** to each point on the curve, and that are vertically
** just above the point.
*"""
HBAR_NORTHEAST = HBarRight(1,-1)


"""* Use horizontal bars that extend from the left y-axis
** to each point on the curve, and that are vertically
** just above point.
*"""
HBAR_NORTHWEST  = HBarLeft(-1,-1)
"""*
** @deprecated
**
** As of version 2.4, this symbol has been redefined to
** be synonymous with the LINE symbol type.
** <p>
**
** Prior to v2.4, this symbol drew a horizontal bar from
** each point to the x coordinate of the previous point.
** Some applications may need to use a revised point set
** in order to produce the same curves using <tt>LINE</tt>
** that they used to produce with this symbol.  <p>
**
** See the discussion within the {@link #VBAR_NEXT
** VBAR_NEXT} symbol for more information about why
** support for these vertically and horizontally constrained
** connecting line symbol types was dropped.
**
** @see #LINE LINE
** @see #HBAR_NEXT HBAR_NEXT
** @see #VBAR_PREV VBAR_PREV
** @see #VBAR_NEXT VBAR_NEXT
**
**
*"""
HBAR_PREV = line
"""* Use horizontal bars that extend from the right y-axis
** to each point on the curve, and that are vertically
** just below the point.
*"""
HBAR_SOUTHEAST = HBarRight(1,1)
"""* Use horizontal bars that extend from the left y-axis
** to each point on the curve, and that are vertically
** just below the point.
*"""
HBAR_SOUTHWEST  = HBarLeft(-1,1)

"""* Use horizontal bars that extend from the left y-axis
** to each point on the curve, and that are vertically
** centered on the point.
*"""
HBAR_WEST  = HBarLeft(-1,0)


"""*
** This symbol type draws a continuous straight line between
** successive individual data points.  By default, the line is
** drawn via an appropriate series of rectangular HTML elements,
** which can produce a "stair-step" look at certain angles.
**
** <small><blockquote> <i>Tip:</i> You can get
** order-of-magnitude faster, and crisper, line charts by
** adding an external vector graphics library to GChart
** via the <tt>setCanvasFactory</tt> method.</small> <p>
**
** Apart from this connecting line, the individual data
** points are displayed exactly as they would have been
** displayed via BOX_CENTER.  <p>
**
** Produces a connecting line similar to what could be
** produced via BOX_CENTER with a fill spacing of 1px,
** except that it uses a more efficient representation
** that merges vertical or horizontal "dot blocks" into
** single HTML elements whenever possible.
** <p>
**
** To produce a line without showing the individual data
** points as separate rectangular symbols, set width and
** height to match your symbol's specified
** <tt>fillThickness</tt>.
**
** @see #BOX_CENTER BOX_CENTER
** @see #setCanvasFactory setCanvasFactory
** @see Symbol#setFillThickness setFillThickness
**
**
**
*"""
LINE = line

"""* @deprecated
**
** In GChart 2.3, you had to use this special symbol type
** to get GChart to use an external canvas library to
** draw crisp connecting lines.
** <p>
**
** As of GChart 2.5, the <tt>LINE</tt> symbol type will,
** by default, be rendered with whatever external canvas
** library you provide to GChart via the
** <tt>setCanvasFactory</tt> method.
**
** <p>
**
** So now, <tt>LINE_CANVAS</tt> is just another name
** for <tt>LINE</tt>. Please replace <tt>LINE_CANVAS</tt> with
** <tt>LINE</tt> in your code.
** <p>
**
** <small> Note that <tt>LINE</tt> only draws continuous lines if
** fill spacing (<tt>setFillSpacing</tt>) is <tt>0</tt>. With
** fill spacing > 0, it uses the old HTML-rendering method. Since
** <tt>0</tt> is now the default fill spacing for the
** <tt>LINE</tt> symbol type, normally <tt>LINE</tt> works
** exactly like <tt>LINE_CANVAS</tt> did. But, if you had
** explicitly set the fill spacing, you may have to remove this
** specification, or set it to <tt>0</tt>, to get the same
** behavior you had before with <tt>LINE_CANVAS</tt>.  <p>
** </small>
**
** @see #LINE LINE
** @see #setCanvasFactory setCanvasFactory
** @see Symbol#setFillSpacing setFillSpacing
**
*"""
LINE_CANVAS  = line
"""*
** A symbol type that does not draw any main symbol. Use
** this symbol type for curves whose points exist solely
** for the purpose of positioning their associated
** annotations. Note that if <tt>fillThickness</tt> is
** non-zero, any connecting dots between the points will
** still be drawn.  <p>
**
** Equivalent to using the <tt>BOX_CENTER</tt> symbol
** type, but with the host symbol's width and height both
** set to zero, so that no box symbol is ever visible.
** <p>
**
** On Disabling hover selection feedback via <tt>NONE</tt>:
** <p>
**
** <blockquote><small>
** Note that if the border width of the host symbol is negative,
** consistent with a 0 x 0 px <tt>BOX_CENTER</tt> symbol type, an
** external border will still appear around the
** <tt>SymbolType.NONE</tt> symbol. Because the default hover
** selection border width is <tt>-1</tt>, when passing
** <tt>SymbolType.NONE</tt> to
** <tt>setHoverSelectionSymbolType</tt>, you generally will also
** need to add a code line such as:
**
** <pre>
**   getCurve().getSymbol().setHoverSelectionBorderWidth(0)
** </pre>
** <p>
**
** If your intention is to disable hover selection feedback,
** it's probably easier to just use
** <tt>setHoverSelectionEnabled(False)</tt>, rather than
** setting the hover selection symbol type to <tt>NONE</tt>.
**
**</small></blockquote>
**
** @see #BOX_CENTER BOX_CENTER
** @see Symbol#setFillThickness setFillThickness
** @see Symbol#setHoverSelectionSymbolType
** setHoverSelectionSymbolType
** @see Symbol#setHoverSelectionEnabled setHoverSelectionEnabled
*"""
class SymbolTypeNone (SymbolType):
    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return 0

    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return 0

    def getIconHeight(self, legendFontSize):
        return 0

    def getIconWidth(self, legendFontSize):
        return 0



NONE = SymbolTypeNone(0, 0, 0, 0, 0, 0)
"""*
** Draws a pie slice whose area is shaded using horizontal
** bars.
**
** <p>
** The vertical distance between corresponding edges of
** successive bars is governed by the symbol's fill
** spacing property; the height of each bar is defined by
** the symbol's fill thickness property; the border and
** background of each shading bar are defined by the
** symbol's border color, border width, border style, and background
** color properties.
**
** <p> The radius of the pie slice (length of the non-arc
** sides of the slice) is chosen such that a circle with
** this radius circumscribes the host <tt>Symbol</tt>'s
** width/height determined rectangle. The slice pivot point
** is defined by each point's x,y position, and the
** orientation and size of the slice by the corresponding
** properties (see links below) of the host <tt>Symbol</tt>.
**
** @see Symbol#setFillSpacing setFillSpacing
** @see Symbol#setFillThickness setFillThickness
** @see Symbol#setBorderColor setBorderColor
** @see Symbol#setBorderWidth setBorderWidth
** @see Symbol#setBackgroundColor setBackgroundColor
** @see Symbol#setPieSliceOrientation setPieSliceOrientation
** @see Symbol#setPieSliceSize setPieSliceSize
** @see Curve.Point#setX setX
** @see Curve.Point#setY setY
** @see #PIE_SLICE_VERTICAL_SHADING PIE_SLICE_VERTICAL_SHADING
** @see #PIE_SLICE_HATCHED_SHADING PIE_SLICE_HATCHED_SHADING
** @see #PIE_SLICE_OPTIMAL_SHADING PIE_SLICE_OPTIMAL_SHADING
** @see Symbol Symbol
**
**
*"""
PIE_SLICE_HORIZONTAL_SHADING = PieSliceSymbolType(True, False, False, 0, 0, 0, 0)
"""*
** Draws a pie slice whose area is shaded using vertical
** bars.
** <p>
**
** The horizontal distance between corresponding edges of
** successive bars is governed
** by the symbol's fill spacing property; the width
** of each bar is defined by the symbol's fill thickness
** property; the border and background of each
** shading bar are defined by the symbol's border color,
** border width, and background color properties.
**
** <p> The radius of the pie slice (length of the non-arc
** sides of the slice) is chosen such that a circle with
** this radius circumscribes the host <tt>Symbol</tt>'s
** width/height determined rectangle. The slice pivot point
** is defined by each point's x,y position, and the
** orientation and size of the slice by the corresponding
** properties (see links below) of the host <tt>Symbol</tt>.
**
** @see Symbol#setFillSpacing setFillSpacing
** @see Symbol#setFillThickness setFillThickness
** @see Symbol#setBorderColor setBorderColor
** @see Symbol#setBorderWidth setBorderWidth
** @see Symbol#setBackgroundColor setBackgroundColor
** @see Symbol#setPieSliceOrientation setPieSliceOrientation
** @see Symbol#setPieSliceSize setPieSliceSize
** @see Curve.Point#setX setX
** @see Curve.Point#setY setY
** @see #PIE_SLICE_HORIZONTAL_SHADING PIE_SLICE_HORIZONTAL_SHADING
** @see #PIE_SLICE_HATCHED_SHADING PIE_SLICE_HATCHED_SHADING
** @see #PIE_SLICE_OPTIMAL_SHADING PIE_SLICE_OPTIMAL_SHADING
** @see Symbol Symbol
**
**
*"""
PIE_SLICE_VERTICAL_SHADING = PieSliceSymbolType(False, True, False, 0, 0, 0, 0)
"""*
** Draws a pie slice whose area is shaded using both vertical
** and horizontal bars, which produces a "cross-hatched"
** pattern.
** <p>
**
** The distance between corresponding edges of successive
** bars is governed by the symbol's fill spacing
** property; the thickness of each bar is defined by the
** symbol's fill thickness property; the border and
** background of each shading bar are defined by the
** symbol's border color, border width, border style, and background
** color properties.
**
** <p> The radius of the pie slice (length of the non-arc
** sides of the slice) is chosen such that a circle with
** this radius circumscribes the host <tt>Symbol</tt>'s
** width/height determined rectangle. The slice pivot point
** (i.e. pie center) is defined by each point's x,y position, and the
** orientation and size of the slice by the corresponding
** properties (see links below) of the host <tt>Symbol</tt>.
**
** @see Symbol#setFillSpacing setFillSpacing
** @see Symbol#setFillThickness setFillThickness
** @see Symbol#setBorderColor setBorderColor
** @see Symbol#setBorderWidth setBorderWidth
** @see Symbol#setBackgroundColor setBackgroundColor
** @see Symbol#setPieSliceOrientation setPieSliceOrientation
** @see Symbol#setPieSliceSize setPieSliceSize
** @see Curve.Point#setX setX
** @see Curve.Point#setY setY
** @see #PIE_SLICE_VERTICAL_SHADING PIE_SLICE_VERTICAL_SHADING
** @see #PIE_SLICE_HORIZONTAL_SHADING PIE_SLICE_HORIZONTAL_SHADING
** @see #PIE_SLICE_OPTIMAL_SHADING PIE_SLICE_OPTIMAL_SHADING
** @see Symbol Symbol
**
**
*"""
PIE_SLICE_HATCHED_SHADING = PieSliceSymbolType(True, True, False, 0, 0, 0, 0)
"""*
** Draw a pie slice whose area is shaded using either
** vertical bars or horizontal bars--whichever
** renders the slice more efficiently. Specifically, pie
** slices that are wider than they are tall use horizontal
** shading and pie slices that are taller than they are
** wide use vertical shading. These choices minimize the
** the number of shading bars (and thus memory and time)
** required to render the pie slice.
**
** <p>
**
** The distance between corresponding edges of successive
** bars is governed by the symbol's fill spacing property
** the thickness of each bar is defined by the symbol's
** fill thickness property; the border and background of
** each shading bar are defined by the symbol's border
** color, border width, and background color properties.
** <p>
**
** The pie slice radius is always determined by the
** formula:
**
** <p>
** <blockquote>
**   <pre>
**   sqrt(symbolWidth^2+symbolHeight^2)/2
**   </pre>
** </blockquote>
**
** <p>
** Here <tt>symbolWidth</tt> and <tt>symbolHeight</tt> are the pie
** slice symbol's width and height, in pixels.
** <p>
**
** Note that this formula implies that the pie slice
** radius is the one associated with the circle that
** circumscribes the symbol, that is, the smallest circle
** that is big enough to completely contain the symbol's
** width/height defined bounding rectangle. Equivalently,
** the length of the pie slice radius equals the half the
** length of the diagonal across the symbol's bounding
** rectangle.
**
** <p>
**
** To assure an integral number of shading bars and thus
** improve the visual look of the pie chart, GChart
** automatically rounds the radius to the nearest
** multiple of the specified <tt>fillSpacing</tt>.  For
** example, if the radius computed from the above formula
** were 96 pixels and the <tt>fillSpacing</tt> were 10
** pixels, GChart would actually use a radius of 100 pixels.
**
** <p>
**
** <i>Tip:</i> To produce a pie slice with a radius, r, set
** the symbol's height to 0, and its width to 2*r (or
** visa-versa). To specify the radius in pixels, use the
** symbol's <tt>setWidth</tt> and <tt>setHeight</tt>
** methods; to specify the radius in "model units" (which
** scale up or down with the chart dimensions) use
** <tt>setModelWidth</tt> and <tt>setModelHeight</tt> instead.
**
** <p>
**
**
** <p>
** The slice pivot point (i.e. pie center)
** is defined by each point's x,y position, and the
** orientation and size of the slice by the
** <tt>setPieSliceOrientation</tt> and
** <tt>setPieSliceSize</tt> methods
** of the host <tt>Symbol</tt>.
** <p>
**
** Creating a pie chart from such pie slices requires
** that you define a separate curve for each slice,
** as illustrated in the code below:
**
** {@code.sample ..\..\..\..\..\..\gcharttestapp\src\com\googlecode\gchart\gcharttestapp\client\GChartExample09.java}
**
** <p>
**
** Which produces this: <p>
**
** <img
** src="{@docRoot}/com/googlecode/gchart/client/doc-files/gchartexample09.png">
**
** <p> Note how, because
** <tt>PIE_SLICE_OPTIMAL_SHADING</tt> was used, vertical
** or horizontal shading is automatically selected so as
** to minimize the number of shading bars in each slice.
**
** @see Symbol Symbol
** @see Symbol#setFillSpacing setFillSpacing
** @see Symbol#setFillThickness setFillThickness
** @see Symbol#setBorderColor setBorderColor
** @see Symbol#setBorderWidth setBorderWidth
** @see Symbol#setBackgroundColor setBackgroundColor
** @see Symbol#setPieSliceOrientation setPieSliceOrientation
** @see Symbol#setPieSliceSize setPieSliceSize
** @see Symbol#setWidth setWidth
** @see Symbol#setHeight setHeight
** @see Symbol#setModelWidth setModelWidth
** @see Symbol#setModelHeight setModelHeight
** @see Curve.Point#setX setX
** @see Curve.Point#setY setY
** @see #PIE_SLICE_VERTICAL_SHADING PIE_SLICE_VERTICAL_SHADING
** @see #PIE_SLICE_HORIZONTAL_SHADING PIE_SLICE_HORIZONTAL_SHADING
** @see #PIE_SLICE_HATCHED_SHADING PIE_SLICE_HATCHED_SHADING
**
*"""
PIE_SLICE_OPTIMAL_SHADING = PieSliceSymbolType(False, False, True, 0, 0, 0, 0)

"""*
** Use vertical bars that extend from the x,y position
** associated with each point, to the y position defined
** by the host <tt>Symbol</tt>'s baseline property, and that are
** horizontally centered on the data point.
**
** @see Symbol Symbol
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
**
*"""
VBAR_BASELINE_CENTER = VBarBaseline(0,0)
"""*
** Use vertical bars that extend from the x,y position
** associated with each point, to the y position defined
** by the host <tt>Symbol</tt>'s baseline property, and whose
** right edge passes through the data point.
**
** @see Symbol Symbol
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
**
*"""
VBAR_BASELINE_WEST = VBarBaseline(-1,0)
"""*
** Use vertical bars that extend from the x,y position
** associated with each point, to the y position defined
** by the host <tt>Symbol</tt>'s baseline property, and whose
** left edge passes through the data point.
**
** @see Symbol#setBaseline setBaseline
** @see #HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
** @see #HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
** @see #HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
** @see #VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
** @see #VBAR_BASELINE_EAST VBAR_BASELINE_EAST
** @see #VBAR_BASELINE_WEST VBAR_BASELINE_WEST
**
*"""
VBAR_BASELINE_EAST = VBarBaseline(1,0)
"""*
** @deprecated
**
** As of version 2.4, this symbol has been redefined to
** be synonomous with the LINE symbol type.
** <p>
**
** Prior to v2.4, this symbol drew a vertical bar from
** each point to the y coordinate of the next point. Some
** applications may need to use a revised point set in
** order to produce the same curves with <tt>LINE</tt>
** that they used to produce with this symbol.
** <p>
**
** Support was dropped because:
**
** <p>
** <ol>
**
**   <li>Continued support would have complicated
** implementation of the hover feedback system
** introduced with v2.4 (these are the only symbols whose
** hit-testing-related size depends on preceding or
** subsequent points).<p>
**
**   <li>With the introduction of
** <tt>LINE</tt> the main reason for this, and related,
** vertically (or horizontally) constrained line drawing
** symbol types had been eliminated (had <tt>LINE</tt>
** existed at the beginning, these constrained line drawing
** symbol types would never have been added).
** <p>
**
** </ol>
** <p>
**
** Finally, note that if lines are vertical or horizontal,
** and solidly connected, <tt>LINE</tt> automatically
** collapses them into a single element, so no
** element-based efficiency losses need be associated with
** replacing curves using such rectilinear symbol types
** with equivalent curves rendered via the
** <tt>LINE</tt> symbol type.
** <p>
**
**
** @see #HBAR_PREV HBAR_PREV
** @see #HBAR_NEXT HBAR_NEXT
** @see #LINE LINE
** @see #VBAR_PREV VBAR_PREV
**
*"""
VBAR_NEXT = line

"""* Use vertical bars that extend from the top of the chart
** to each point on the curve, and are horizontally
** centered on the point.
*"""
VBAR_NORTH = VBarTop(0, -1)
"""* Use vertical bars that extend from the top of the chart
** to each point on the curve, and are horizontally
** to the right of the point.
*"""
VBAR_NORTHEAST = VBarTop(1, -1)

"""* Use vertical bars that extend from the top of the chart
** to each point on the curve, and are horizontally
** to the left of the point.
*"""
VBAR_NORTHWEST = VBarTop(-1, -1)
"""*
** @deprecated
**
** As of version 2.4, this symbol has been redefined to
** be synonomous with the LINE symbol type.
** <p>
**
** Prior to v2.4, this symbol drew a vertical bar from
** each point to the y coordinate of the previous point.
** Some applications may need to use a revised point set
** in order to produce the same curves using <tt>LINE</tt>
** that they used to produce with this symbol.  <p>
**
** See the discussion within the {@link #VBAR_NEXT
** VBAR_NEXT} symbol for more information about why
** support for these vertically and horizontally constrained
** connecting line symbol types was dropped.
**
** @see #LINE LINE
** @see #HBAR_PREV HBAR_PREV
** @see #HBAR_NEXT HBAR_NEXT
** @see #VBAR_NEXT VBAR_NEXT
**
*"""

VBAR_PREV = line

"""* Use vertical bars that extend from the x-axis
** to each point on the curve, and that are horizontally
** centered on the point.
*"""
VBAR_SOUTH = VBarBottom(0, 1)
"""* Use vertical bars that extend from the x-axis
** to each point on the curve, and that are horizontally
** to the right of the point.
*"""
VBAR_SOUTHEAST = VBarBottom(1, 1)

"""* Use vertical bars that extend from the x-axis
** to each point on the curve, and that are horizontally
** to the left of the point.
*"""
VBAR_SOUTHWEST = VBarBottom(-1, 1)
"""*
** Represents a single x-axis grid-line. You can use
** this symbol to draw a single vertical bar
** across the chart.
**
*"""
class SymbolTypeXGrid (SymbolType):
    def getAdjustedHeight(self, height, y, yPrev, yNext, yMin, yMax, yMid):
        return yMax - yMin

    def getUpperLeftY(self, height, y, yPrev, yNext, yMin, yMax, yMid, yMouse):
        return yMin

    def getIconHeight(self, legendFontSize):
        return legendFontSize

    def getIconWidth(self, legendFontSize):
        return 1



XGRIDLINE = SymbolTypeXGrid(0,0,0,0,0.5,0.5,False)
"""*
** Represents a single y-axis (or y2-axis) grid-line. You
** can use this symbol to draw a single horizontal line (or
** bar) across the chart, for example, to display an upper
** bound or control limit.
**
*"""
class SymbolTypeYGrid (SymbolType):
    def getAdjustedWidth(self, width, x, xPrev, xNext, xMin, xMax, xMid):
        return xMax - xMin

    def getUpperLeftX(self, width, x, xPrev, xNext, xMin, xMax, xMid, xMouse):
        return xMin

    def getIconHeight(self, legendFontSize):
        return 1

    def getIconWidth(self, legendFontSize):
        return legendFontSize



YGRIDLINE = SymbolTypeYGrid(0,0,0.5,0.5,0,0, True)

"""*
**  @deprecated
**
** This symbol is the same as <tt>YGRIDLINE</tt> and
** was added by mistake in version 1.
** (the y-axis isn't defined by the symbol type, but
**  rather by the curve's <tt>setYAxis</tt> method).
** <p>
** Please use <tt>YGRIDLINE</tt> instead.
**
** @see #YGRIDLINE YGRIDLINE
** @see GChart.Curve#setYAxis setYAxis
**
*"""

Y2GRIDLINE = YGRIDLINE

"""*
** The default symbol type for curve if none is
** specified; this default is BOX_CENTER
**
** @see SymbolType#BOX_CENTER BOX_CENTER
** @see Symbol#setSymbolType setSymbolType
**
*"""
DEFAULT_SYMBOL_TYPE = BOX_CENTER

