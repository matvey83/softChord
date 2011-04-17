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
from pyjamas.chart.Point import Point
from pyjamas.chart.Symbol import Symbol

from pyjamas.chart.GChartConsts import Y_AXIS
from pyjamas.chart.GChartConsts import Y2_AXIS
from pyjamas.chart.GChartConsts import N_PRE_SYSTEM_CURVES
from pyjamas.chart.GChartConsts import NAI
from pyjamas.chart import GChartWidgets


"""*
* Represents a curve on a chart, which includes
* information such as the x,y coordinates of each point,
* the symbol used to represent points on the curve, etc.
* <p>
* To create a curve, use the <tt>addCurve</tt>
* method.
*
* @see GChart#addCurve() addCurve()
*
"""

EXTRA_BANDS = 2;   # far left, right (top, bottom) bands

class Curve:

    def isValidated(self):
        return self.validated

    """
    * TestGChart14d revealed that curves.indexOf(curve) could, due to its
    * sequential search, create a performance bug if the chart had
    * over 100 curves (e.g. the 160 pie chart slices/curves of TestGChart14d)
    * <p>
    *
    * With a little extra bookkeeping during add/remove curve to call these
    * methods (and the extra int) this problem was corrected.
    *
    *
    """
    def incrementIndex(self):
        self.indexOf += 1

    def decrementIndex(self):
        self.indexOf -= 1

    def clearIndex(self):
        self.indexOf = NAI

    def getIndexOf(self):
        return self.indexOf

    """
    def assertCurveNotRemoved(self):
        if self.indexOf == NAI:
            raise IllegalStateException(
            "Removed curves should not be modified. " +
            "You removed a curve, but retained a reference " +
            "to that curve, and then tried to modify one of " +
            "its properties after you removed it.")


    """
    """
    * No constructor because curves are always
    * contained within, and managed by, their containing
    * GChart via its addCurve, removeCurve, and related
    * methods.
    *
    """
    def __init__(self, chart, indexOf=NAI):
        self.chart = chart
        self.wasCanvasRendered = False
        self.visible = True
        self.legendHTML = None
        self.points = []
        # symbol defines how every point on this curve is rendered
        self.symbol = Symbol(self)

        self.yAxisId = Y_AXIS
        self.validated = False
        self.indexOf = indexOf

        self.bandList = None # index of first point in each band
        self.bandThickness = Double.NaN

    """*
    * Adds a point at the specified position in the point
    * sequence, increasing the indexes of existing points at or after
    * the specified position by 1.
    *
    * @param iPoint the position that the point will occupy
    * @param x the x-coordinate of the point (model units)
    * @param y the y-coordinate of the point (model units)
    *
    * @see #getPoint getPoint
    * @see #addPoint(double, double) addPoint(double,double)
    * @see #removePoint removePoint
    * @see #clearPoints clearPoints
    * @see #getNPoints getNPoints
    """
    def addPoint(self, arg1, arg2, arg3=None):
        self.invalidate()
        if arg3 is None:
            x = arg1
            y = arg2
            self.points.append(Point(self, x, y))
        else:
            iPoint = arg1
            x = arg2
            y = arg3
            self.points.insert(iPoint, Point(self, x, y))


    """*
    * Removes every point this curve contains.
    *
    * @see Point Point
    * @see #getPoint getPoint
    * @see #addPoint(double, double) addPoint(double,double)
    * @see #addPoint(int,double,double) addPoint(int,double,double)
    * @see #removePoint removePoint
    * @see #getNPoints getNPoints
    """
    def clearPoints(self):
        if self == self.getParent().getTouchedCurve():
            self.chart.plotPanel.touch(None)

        self.invalidate()
        del self.points
        self.points = []



    """
    * Locates index of vertical or horizontal hit-testing band
    * that the given point appears in. The first and last
    * "pseudo-bands" are devoted to holding all points that fall
    * either to the left of or to the right of (or above or below
    * for horizontal banding) the first or last "normal" band
    * covering the decorated chart's containing "box".
    * <p>
    *
    * Note that some points just slightly off the right or bottom edge
    * may not end up in a pseudo-band, due to the fact that the chart
    * width (or height) need not be an even multiple of the (fixed) band
    * thickness (the "last band sticking out a bit" effect).
    *
    """
    def getBand(self, iPoint, bandThickness):
        result = NAI
        symType = self.getSymbol().getSymbolType()
        xPx = symType.getCenterX(self.chart.plotPanel, self.getSymbol(), iPoint)
        if Double.NaN==(xPx):
            return result; # NaN points not in any band

        yPx = symType.getCenterY( self.chart.plotPanel, self.getSymbol(),
                                  iPoint, self.onY2())
        if Double.NaN==(yPx):
            return result; # NaN points not in any band

        # now, we've got a point with x,y values in some sort of band

        if self.getSymbol().isHorizontallyBanded():
            if yPx < 0:
                result = 0; # off-chart point above chart

            elif yPx >= (len(self.bandList)-EXTRA_BANDS)*bandThickness:
                result = len(self.bandList)-1; # off-chart point below chart

            else:
                # inside a normal, chart-covering, band
                result = 1 + int ( math.floor(yPx/bandThickness) )


        else:
            # vertically banded
            if xPx < 0:
                result = 0;  # off-chart point to the left

            elif xPx >= (len(self.bandList)-EXTRA_BANDS)*bandThickness:
                result = len(self.bandList)-1; # off-chart point to the right

            else:
                # within one of the real bands covering the chart
                result = 1 + int ( math.floor(xPx/bandThickness) )


        return result


    """
    * Number of hit-test bands for this curve, for a given band
    * thickness.
    *
    """
    def getNBands(self, bandThickness):
        result = EXTRA_BANDS
        if self.getSymbol().isHorizontallyBanded():
            result += int(math.ceil(self.chart.getYChartSize()/bandThickness))

        else :
            result += int(math.ceil(self.chart.getXChartSize()/bandThickness))

        return result


    """
    * Separates points on this curve into bins associated with
    * successive vertical (or horizontal) bands across the entire
    * decorated chart.
    * <p>
    *
    * Because busy charts typically distribute points evenly
    * across the chart, by jumping to the appropriate band's
    * list, we can (usually) greatly accelerate worst case mouse
    * hit testing. And because the bin organizing step only
    * requires a single pass over all the points (and less than a
    * two int memory overhead per point) it should almost always
    * be a "good deal" performance-wise (compared to a simple
    * full point-list scan with every hit test).<p>
    *
    * Points are placed into bins based on the (pixel) position
    * of the x (or, with horizontal bands, y) at the center of
    * the rendered symbol.  We choose bin size to guarantee that
    * bins are at least as wide (or high, for horizontally banded
    * hit testing) as the rendered symbols on this curve. This
    * simplifies hit testing, since bins are big enough to assure
    * that a single symbol straddles at most two adjacent bands.
    * Exploits fact that all symbols on the same curve have the
    * same size, and that curves with many points on them tend to
    * have smaller sized symbols.
    *
    * <p>
    *
    * Note that, for bin placement purposes, pie slices are
    * considered to have a "center" equal to the center of the
    * pie that contains them, and to have a width and height
    * equal to the diameter of the pie containing the slice
    * (the "worst-case slice").
    *
    * <p>
    *
    * Also note that a symbol whose center is in the right side
    * of a vertical band may overlap into the following band, and
    * one in the left side may overlap the preceding band. Thus
    * during hit testing, we must check not only the lists of
    * points in the bands "touched" by the mouse-cursor-centered
    * brush, but also 1) the band to the immediate left of the
    * leftmost touched band, whenever a left-side sub-band of that band
    * is touched by the brush and 2) the band to the immediate
    * right of the rightmost touched band, whenever a right-side
    * sub-band of that band is touched. The thickness of these left
    * and right side sub-bands equals half the symbol width.
    * Expanding the brush a half-symbol width on either edge
    * is the easiest way to apply these rules. Exactly
    * analogous statements apply to horizontal bands.  <p>
    *
    * A minimum band size is enforced to prevent the number of
    * bands from growing too large with small symbols. Each
    * symbol type defines if vertical or horizontal banding is
    * more appropriate, or if brush shape should determine
    * banding strategy (as of this writing, only horizontal bar
    * symbol types require horizontal hit-test bands).  Exploits the
    * fact that all symbols have a fixed size for at least one of
    * their dimensions (for example, vertical bars have variable
    * height but fixed width).<p>
    *
    * Note: this method must be called after the curve is
    * rendered during an update(), to assure that hit-test-bins
    * are consistent with rendered curves, and ready for use
    * before the first mouse hit testing is done.
    * <p>
    *
    * After running this method, points on this curve within a given
    * band can be enumerated as in the following code:
    * <p>
    *
    * <pre>
    Point p = None
    forloop (int iPoint = bandList[iBand]; iPoint != NAI; iPoint = p.getINextInBand()) {
        p = getPoint(iPoint)
        # do something requiring points in a given band...


    * </pre>
    *
    """
    def clearBandList(self):
        self.bandList = None

    def bandSeparatePoints(self):
        self.bandThickness = \
            self.getSymbol().getSymbolType().getBandThickness(self.chart.plotPanel,
                                                         self.getSymbol(),
                                                         self.onY2())
        nBands = self.getNBands(self.bandThickness)

        if self.bandList is None  or  len(self.bandList) != nBands:
            self.bandList = []
            for i in range(nBands):
                self.bandList.append(NAI)
        for i in range(nBands):
            self.bandList[i] = NAI

        for iPoint in range(self.getNPoints()):
            iBand = self.getBand(iPoint, self.bandThickness)
            p = self.getPoint(iPoint)
            if NAI == iBand:
                # point isn't rendered at all, so isn't in a band (a next
                # link pointing to self means "I'm not in any band"). To let
                # us skip over these points quickly during rendering.
                p.setINextInBand(iPoint)

            else:
                # Add point to front of list for whatever band it's in
                # (note that point order therefore gets reversed).
                p.setINextInBand(self.bandList[iBand])
                self.bandList[iBand] = iPoint




    """
    * Returns the index of the point on this curve whose rendered
    * symbol intersects a rectangle with the specified width and
    * height centered on the specified point (this rectangle is
    * typically a point selection "brush", centered on the mouse
    * cursor).  <p>
    *
    * In the event that more than one point's rendered symbol
    * intersects with the specified rectangle, the point whose
    * center is closest to the specified rectangle's center is
    * returned. In the event of a tie, the point with the largest
    * point index is returned. If no point "touches" the rectangle,
    * <tt>NAI</tt> is returned.  <p>
    *
    * Assumes/requires up-to-date <tt>bandList</tt> array and
    * related <tt>iNextInBand</tt> indexes (these get defined within
    * the <tt>bandSeparatePoints</tt> method).
    *
    """

    def getClosestTouchingPoint(self, xBrush, yBrush):

        result = NAI
        # ANCHOR_MOUSE symbol type curves not band separated/hit tested
        if None == self.bandList:
            return result

        symType = self.getSymbol().getSymbolType()
        dBest = Double.MAX_VALUE; # closest touching pt's distance^2




        brushWidth = symType.getBrushWidth(self.getSymbol())
        """
        * In every tested browser EXCEPT FF3, we don't need the +1 below to
        * select a 1px tall, off-chart, symbol with a 1x1 px brush
        * (specifically, to select the leftmost vertical bar on TestGChart28).
        * The +1  below in effect adds 1 px to the height of the brush to
        * workaround this problem.
        *
        """
        brushHeight = symType.getBrushHeight(self.getSymbol()) + 1
        brushLocation = symType.getBrushLocation( self.getSymbol())
        nBands = len(self.bandList)

        # Determine range of bands touched by brush, taking into
        # account potential for symbols whose centers are in one
        # band to "stick out" into an adjacent band by half-band
        # thickening of either end of the brush.
        #
        # Note that the 0th and (nBand-1)th bands represent
        # "pseudo-bands" that hold all points that fall to the left
        # or right (or above or below if horizontally banded) the
        # rectangle occupied by the decorated chart.  The tacit
        # assumption is that such completely off-the-chart points
        # are rare, so it's OK to bunch them up into just 2 bands.
        if self.getSymbol().isHorizontallyBanded():
            # horizontal bars and some curves with "wider than high" brushes
            top = brushLocation.getUpperLeftY(yBrush, brushHeight, 0)
            bottom = top + brushHeight
            top -= self.bandThickness/2.
            bottom += self.bandThickness/2.
            iBandFirst = int( max(0, min(nBands-1,1+math.floor(
                                        top / self.bandThickness))))
            iBandLast = int ( max(0, min(nBands-1, 1+math.floor(
                                        bottom / self.bandThickness))))

        else:
            # vertical bars, some curves with "tall or square" brushes
            left = brushLocation.getUpperLeftX(xBrush, brushWidth, 0)
            right = left + brushWidth
            left -= self.bandThickness/2.0
            right += self.bandThickness/2.0
            iBandFirst = int( max(0, min(nBands-1, 1+math.floor(
                                        left / self.bandThickness))))
            iBandLast = int( max(0, min(nBands-1, 1+math.floor(
                                        right / self.bandThickness))))


        # Every point whose symbol touches the brush must be in one
        # of these bands. Search them to find closest touching point.
        for iBand in range(iBandFirst, iBandLast+1):
            p = None
            iPoint = self.bandList[iBand]
            while iPoint != NAI:
                if iPoint < 0  or  iPoint >= self.getNPoints():
                    raise IllegalStateException(
                        "Inappropriately terminated band-point-list, GChart bug likely. " +
                        "iPoint=" + iPoint + " nPoints=" + self.getNPoints() +
                        " iBand="+iBand+" iBandFirst="+iBandFirst+" iBandLast="+iBandLast +
                        " xBrush="+xBrush+" yBrush="+yBrush+" brushWidth="+brushWidth +
                        " brushHeight=" +brushHeight + " bandThickness=" + self.bandThickness)

                p = self.getPoint(iPoint)
                if symType.isIntersecting(self.chart.plotPanel,
                                          self.getSymbol(), iPoint,
                                          self.onY2(), xBrush, yBrush,
                                          brushWidth, brushHeight):
                    # this point touches the brush (keep it if closest)
                    xPoint = symType.getCenterX(self.chart.plotPanel,
                                                self.getSymbol(), iPoint)
                    yPoint = symType.getCenterY(self.chart.plotPanel,
                                                self.getSymbol(), iPoint,
                                                self.onY2())
                    dx = self.getSymbol().xScaleFactor*(xPoint-xBrush)
                    dy = self.getSymbol().yScaleFactor*(yPoint-yBrush)
                    d = dx*dx + dy*dy
                    if d < dBest:
                        result = iPoint
                        dBest = d

                    elif d == dBest  and  iPoint > result:
                        # in the case of ties, choose largest point index
                        # (highest "z-order" -- the one "on top")
                        result = iPoint
                        dBest = d



                iPoint = p.getINextInBand()



        return result



    """*
    * @deprecated
    *
    * This method is equivalent to:
    * <p>
    *<tt>getSymbol().getHovertextTemplate()</tt>
    * <p>
    *
    * It is retained only for GChart 1.1 compatibility purposes.
    *
    * @see Symbol#getHovertextTemplate() Symbol.getHovertextTemplate
    *
    """
    def getHovertextTemplate(self):
        return symbol.getHovertextTemplate()


    """*
    ** Returns the HTML defining this curve's legend label.
    **
    ** @return the legend label HTML for this curve
    **
    ** @see #setLegendLabel setLegendLabel
    **
    *"""
    def getLegendLabel(self):
        return self.legendHTML


    """*
    * Returns the number of points this curve contains.
    *
    * @return the number of points this curve contains.
    *
    * @see #getPoint getPoint
    * @see #addPoint(double, double) addPoint(double,double)
    * @see #addPoint(int,double,double) addPoint(int,double,double)
    * @see #removePoint removePoint
    * @see #clearPoints clearPoints
    """
    def getNPoints(self):
        return len(self.points)


    """*
    * Returns a reference to the GChart that contains this
    * curve.
    *
    * @return GChart that contains this curve--its "parent".
    *
    """
    def getParent(self):
        return self.chart

    """*
    * Returns a reference to the point at the specified
    * index.  The returned reference can be used to modify
    * various properties of the point, such as
    * its optional annotation (text label).
    *
    * <p>
    * @param iPoint the index of the point to be returned.
    * @return a reference to the Point at the specified index.
    *
    * @see #addPoint(double, double) addPoint(double,double)
    * @see #addPoint(int,double,double) addPoint(int,double,double)
    * @see #removePoint removePoint
    * @see #clearPoints clearPoints
    * @see #getNPoints getNPoints
    """
    def getPoint(self, iPoint=None):
        if iPoint is None:
            iPoint = self.getNPoints()-1

        if iPoint < 0  or  iPoint >= len(self.points):
            raise IllegalArgumentException(
            "Point index iPoint=" + iPoint + ". " +
            "is either < 0 or >= the number of points on the curve.")

        return self.points[iPoint]



    """*
    * Returns the positional index (within this curve's list of
    * points) of the specified point.
    * <p>
    *
    * Returns <tt>NAI</tt> if the specified point is not found on
    * this curve's point list.
    *
    * <p>
    * @param point point whose list position is to be retrieved
    * @return position of point on this curve's point list, or
    *        <tt>NAI</tt>
    *        if not on the list.
    *
    * @see #getPoint() getPoint()
    * @see #getPoint(int) getPoint(int)
    * @see #addPoint addPoint
    * @see #removePoint removePoint
    * @see #clearPoints clearPoints
    * @see #getNPoints getNPoints
    """
    def getPointIndex(self, point):
        try:
            return self.points.index(point)
        except ValueError:
            return NAI

    """*
    ** Returns the symbol associated with this curve.
    ** <p>
    **
    ** Though you cannot set the symbol itself (there is no
    ** <tt>setSymbol</tt> method) you can have essentially
    ** the same effect by setting the <tt>SymbolType</tt> (to get
    ** qualitatively different kinds of symbols, e.g.
    ** bar-chart bars vs. boxes) and by changing symbol
    ** attributes such as background color, height, and
    ** width.
    **
    ** @return the symbol used to represent points on this curve
    **
    ** @see Symbol#setSymbolType Symbol.setSymbolType
    ** @see Symbol#setBackgroundColor Symbol.setBackgroundColor
    ** @see Symbol#setBorderWidth Symbol.setBorderWidth
    ** @see Symbol#setBorderStyle Symbol.setBorderStyle
    ** @see Symbol#setWidth Symbol.setWidth
    ** @see Symbol#setHeight Symbol.setHeight
    ** @see Symbol#setModelWidth Symbol.setModelWidth
    ** @see Symbol#setModelHeight Symbol.setModelHeight
    **
    *"""
    def getSymbol(self):
        return self.symbol


    """*
    * Returns the y-axis (Y_AXIS or Y2_AXIS) this curve is
    * plotted on.
    *
    * @return an identifier, either Y_AXIS, or Y2_AXIS, indicating
    *   if this curve is plotted on the left (y) or right (y2) y-axis
    *
    ** @see #setYAxis setYAxis
    ** @see GChart#Y_AXIS Y_AXIS
    ** @see GChart#Y2_AXIS Y2_AXIS
    **
    """
    def getYAxis(self):
        return self.yAxisId


    """* Is this curve visible on the chart and legend key,
    ** or is it hidden from view.
    **
    ** @return True if the curve is visible, False otherwise.
    **
    ** @see #setVisible setVisible
    *"""
    def isVisible(self):
        return self.visible

    """* Convenience method equivalent to <tt>getYAxis()==Y2_AXIS</tt>.
    *
    * @return True if curve is on second y-axis, else False
    *
    * @see #getYAxis getYAxis
    """
    def onY2(self):
        return self.yAxisId == Y2_AXIS

    """*
    * Removes the point at the specified index.
    *
    * @param iPoint index of point to be removed.
    *
    * @see #getPoint getPoint
    * @see #addPoint(double, double) addPoint(double,double)
    * @see #addPoint(int,double,double) addPoint(int,double,double)
    * @see #clearPoints clearPoints
    * @see #getNPoints getNPoints
    """
    def removePointByIndex(self, iPoint):
        if iPoint < 0  or  iPoint >= getNPoints():
            raise IllegalArgumentException(
            "iPoint=" + iPoint + " iPoint arg must be >= 0 and < " +
            getNPoints() + ", the number of points on the curve.")

        self.invalidate()

        # simulate user moving away from point before it is deleted
        # (this assures that any required hoverCleanup gets called,
        #  and clears the otherwise dangling reference to the point)
        if self.chart.plotPanel.touchedPoint == self.getPoint(iPoint):
            self.chart.plotPanel.touch(None)

        self.points.remove(iPoint)


    """*
    * Removes the given point from this curve.
    * <p>
    *
    * If the given point is not on this curve, or is
    * <tt>None</tt>, an exception is thrown.
    *
    * @param p the point to be removed.
    *
    *
    """
    def removePoint(self, p):
        if not isinstance(p, Point):
            self.removePointByIndex(p)
            return

        if None == p:
            raise IllegalArgumentException("p cannot be None.")

        index = self.getPointIndex(p)
        if NAI == index:
            raise ValueError(
                "p must be a point on this curve (whose curveIndex is %d)" % \
                        self.getParent().getCurveIndex(self))

        self.removePoint(index)

    """*
    ** @deprecated
    **
    ** This method is equivalent to:
    ** <p>
    **  <tt>getSymbol().setHovertextTemplate(hovertextTemplate)</tt>
    ** <p>
    ** It is retained only for GChart 1.1 compatibility purposes.
    **
    ** @see Symbol#setHovertextTemplate Symbol.setHovertextTemplate
    *"""
    def setHovertextTemplate(self, hovertextTemplate):
        symbol.setHovertextTemplate(hovertextTemplate)

    """*
    ** Sets the HTML that defines the label shown to the
    ** right of the icon representing the curve's symbol in
    ** the chart's legend.
    **
    ** <p>
    ** Setting the legend label to <tt>None</tt> removes the
    ** entire row (the label and the icon) associated with
    ** this curve from the chart key.
    ** <p>
    ** Note that, since <tt>None</tt> is the default, unless
    ** you set at least one legend label, no chart key will
    ** appear at all.
    **
    ** @param legendHTML the HTML defining this curve's legend label.
    **                   or <tt>None</tt> to remove the curve from
    **                   the legend entirely.
    **
    ** @see #getLegendLabel getLegendLabel
    ** @see GChart#setLegendThickness setLegendThickness
    **
    *"""
    def setLegendLabel(self, legendHTML):
        self.chartDecorationsChanged = True
        self.legendHTML = legendHTML

    """*
    ** Defines if this curve is visible both in the plotting
    ** region and on the legend key.
    ** <p>
    **
    ** <i>Notes:</i>
    **
    ** <ol>
    **  <li>A curve must also have a non-<tt>None</tt> legend label
    ** if it is to appear on the legend key.
    ** <p>
    **
    **  <li>Hidden curves are excluded from the computation
    ** of any auto-computed axis limits.
    **
    ** </ol>
    **
    ** @param isVisible False to hide curve, True to reveal it.
    **
    ** @see #isVisible() isVisible
    ** @see #setLegendLabel setLegendLabel
    **
    *"""
    def setVisible(self, visible):
        """ Axis curve count bookkeeping requires that curve be on the
        * list of curves.
        * <p>
        *
        * Developer refs to removed curves could screw up this
        * bookkeeping.
        * <p>
        *
        * Though often this would be a developer error, best not to
        * raise an exception because some developers could use deleted
        * curves as repositories for curve state data, or an event
        * sequence might produce setVisible calls through a dangling
        * curve reference after a curve had been removed, and best to
        * let developer get away with that kind of thing.  <p>
        *
        * No point in invalidating since removed curves can never
        * become part of a rendered GChart again.
        *
        """

        if self.getIndexOf() == NAI:
            self.visible = visible
            return


        self.invalidate()

        # hover selection feedback curves (which are system curves)
        # never impact curve counts, need to refresh decorations, etc.
        if self.isSystemCurve():
            self.visible = visible
            return


        if self.visible != visible:
            if self.getYAxis() == Y_AXIS:
                yaxis = self.chart.getYAxis()
            else:
                yaxis = self.chart.getY2Axis()
            if visible:
                axisCreatedOrDestroyed = (yaxis.getNCurvesVisibleOnAxis() == 0)
                self.chart.getXAxis().incrementCurves()
                yaxis.incrementCurves()

            else:
                self.chart.getXAxis().decrementCurves()
                yaxis.decrementCurves()
                axisCreatedOrDestroyed = (yaxis.getNCurvesVisibleOnAxis() == 0)


            if (None != self.getLegendLabel()  and  self.isLegendVisible())  or  axisCreatedOrDestroyed:
                self.chartDecorationsChanged = True


            self.visible = visible



    """* Sets the y-axis that this curve is plotted on.
    ** <p>
    ** @param axisId must be either Y_AXIS or
    **               Y2_AXIS
    **
    ** @see #getYAxis getYAxis
    ** @see GChart#Y_AXIS Y_AXIS
    ** @see GChart#Y2_AXIS Y2_AXIS
    **
    **
    *"""
    def setYAxis(self, axisId):
        self.invalidate()
        if self.isSystemCurve():
            self.yAxisId = axisId

        elif axisId != self.yAxisId:
            if axisId == Y2_AXIS:
                # from Y to Y2
                self.chart.getYAxis().decrementCurves()
                self.chart.getY2Axis().incrementCurves()

            else:
                # from Y2 to Y
                self.chart.getY2Axis().decrementCurves()
                self.chart.getYAxis().incrementCurves()

            self.yAxisId = axisId



    # Is this specific curve actually clipped to the plot area?
    def getActuallyClippedToPlotArea(self):
        result = self.getParent().getClipToPlotArea()
        if result:
            # decorative, hover feedback curves are never clipped
            rpIndex = self.chart.getRenderingPanelIndex(self.getIndexOf())
            if (GChartWidgets.DECORATIVE_RENDERING_PANEL_INDEX == rpIndex  or
                self.chart.isHoverFeedbackRenderingPanel(rpIndex)):
                result = False


        return result


    """
    * Is this curve one of GChart's special, internally created, system
    * curves? These curves can't be directly accessed by users, and are
    * used by GChart to render special features of the chart, such as
    * the hover selection cursors, titles, footnotes, etc.
    *
    """
    def isSystemCurve(self):
        # negative curve indexes are reserved for system curves
        result = ((self.indexOf != NAI)  and
                    self.getParent().externalCurveIndex(self.indexOf) < 0)
        return result

    # renders the specified point of this curve on the given panel
    def realizePoint(self, pp, grp, arp, iPoint):
        p = self.points[iPoint]
        x = p.getX()
        y = p.getY()
        # skip points at undefined locations
        if (Double.NaN==(x))  or  (Double.NaN==(y)):
            return

        prevX = Double.NaN
        prevY = Double.NaN
        if iPoint > 0:
            prevP = self.points[iPoint-1]
            prevX = prevP.getX()
            prevY = prevP.getY()

        nextX = Double.NaN
        nextY = Double.NaN
        nextP = None
        if iPoint < self.getNPoints()-1:
            nextP = self.points[iPoint+1]
            nextX = nextP.getX()
            nextY = nextP.getY()


        # if point was not assigned to any band, it's not drawn
        # at all (undefined x or y, or off chart entirely)
        drawMainSymbol = (p.getINextInBand() != iPoint)

        self.getSymbol().realizeSymbol(pp, grp, arp, p.getAnnotation(),
                                    self.onY2(),
                                    self.getActuallyClippedToPlotArea(),
                                    self.getParent().getClipToDecoratedChart(),
                                    drawMainSymbol,
                                    x, y, prevX, prevY, nextX, nextY)
        #    }


    """
    * Declares that this curve's rendering panel (its DOM representation)
    * is inconsistent with current curve specifications.
    *
    * <p>
    *
    * Sets the flag <tt>update</tt> uses to determine if a curve needs
    * to be re-rendered.
    *
    """
    def invalidate(self):
        # The guard isn't just for speed; it keeps us out of trouble
        # when the system curves are being added/configured initially
        if self.validated:
            self.validated = False
            # for efficiency, all background curves use a single rendering
            # panel, so invalidating one background curve invalidates them all
            if self.indexOf < N_PRE_SYSTEM_CURVES:
                for i in range(N_PRE_SYSTEM_CURVES):
                    self.chart.curves[i].validated = False




    """
    * Smallest rectangle containing curve's graphics (ignoring
    * annotations)
    * <p>
    *
    * Each curve has it's own canvas to allow for fast, single
    * curve, updates (and we hope this rendering independence will
    * facilitate additional features in future releases). So, we
    * have to economize on canvas size.  Moreover, because we
    * allow rendering outside of the decorated chart region, we
    * can't just set the size of the canvas to the size of the
    * plot area or decorated chart (even if we could afford to do
    * that, memory-wise).
    *
    """
    def getContainingRectangle(self, pp):
        result = GChartWidgets.Rectangle()
        if self.getNPoints() == 0:
            result.x = result.y = result.width = result.height = 0
            return result


        minX = Double.MAX_VALUE
        maxX = -Double.MAX_VALUE
        minY = Double.MAX_VALUE
        maxY = -Double.MAX_VALUE
        pointAtXAxisMin = False; # do keyword positioned points
        pointAtXAxisMax = False; # exist on this curve?
        pointAtYAxisMin = False
        pointAtYAxisMax = False
        isClippedToDecoratedChart = self.chart.getClipToDecoratedChart()
        isClippedToPlotArea = self.getActuallyClippedToPlotArea()
        # Find min, max for x,y and record each keyword position used
        nPoints = self.getNPoints()
        for i in range(nPoints):
            p = self.getPoint(i)
            x = p.getX()
            y = p.getY()
            if Double.MAX_VALUE == x:
                pointAtXAxisMax = True

            elif -Double.MAX_VALUE == x:
                pointAtXAxisMin = True

            else:
                if x < minX:
                    minX = x

                if x > maxX:
                    maxX = x


            if Double.MAX_VALUE == y:
                pointAtYAxisMax = True

            elif -Double.MAX_VALUE == y:
                pointAtYAxisMin = True

            else:
                if y < minY:
                    minY = y

                if y > maxY:
                    maxY = y




        # apply "at min/max" keyword, clipping imposed limits
        if pointAtXAxisMin:
            minX = min(minX, pp.getXMin())

        if isClippedToPlotArea:
            minX = max(minX, pp.getXMin())

        elif isClippedToDecoratedChart:
            minX = max(minX, getXAxis().pixelToModel(0))


        if pointAtXAxisMax:
            maxX = max(maxX, pp.getXMax())

        if isClippedToPlotArea:
            maxX = min(maxX, pp.getXMax())

        elif isClippedToDecoratedChart:
            maxX = min(maxX, getXAxis().pixelToModel(
            pp.getXChartSizeDecoratedQuickly()))


        onY2 = self.onY2()
        if onY2:
            if pointAtYAxisMin:
                minY = min(minY, pp.getY2Min())

            if isClippedToPlotArea:
                minY = max(minY, pp.getY2Min())

            elif isClippedToDecoratedChart:
                minY = max(minY, getY2Axis().pixelToModel(
                pp.getYChartSizeDecoratedQuickly()))

            if pointAtYAxisMax:
                maxY = max(maxY, pp.getY2Max())

            if isClippedToPlotArea:
                maxY = min(maxY, pp.getY2Max())

            elif isClippedToDecoratedChart:
                maxY = min(maxY, getY2Axis().pixelToModel(0))

        else:
            if pointAtYAxisMin:
                minY = min(minY, pp.getYMin())

            if isClippedToPlotArea:
                minY = max(minY, pp.getYMin())

            elif isClippedToDecoratedChart:
                minY = max(minY, self.chart.getYAxis().pixelToModel(
                pp.getYChartSizeDecoratedQuickly()))

            if pointAtYAxisMax:
                maxY = max(maxY, pp.getYMax())

            if isClippedToPlotArea:
                maxY = min(maxY, pp.getYMax())

            elif isClippedToDecoratedChart:
                maxY = min(maxY, self.chart.getYAxis().pixelToModel(0))



        # finally, we need to convert to pixels while taking into account
        # the size of the rendered symbol itself (e.g. pies can stick
        # out from their x,y specified center point, etc.)
        sym = self.getSymbol()
        symType = sym.getSymbolType()
        # in obscure cases, canvas could clip without this extra wiggle room
        extraSpace = sym.getFillThickness()
        extraSpace += abs(sym.getBorderWidth())
        left0 = symType.getEdgeLeft(pp, sym, minX, onY2)
        left1 = symType.getEdgeLeft(pp, sym, maxX, onY2)
        right0 = symType.getEdgeRight(pp, sym, minX, onY2)
        right1 = symType.getEdgeRight(pp, sym, maxX, onY2)
        bottom0  = symType.getEdgeBottom(pp, sym, minY, onY2)
        bottom1  = symType.getEdgeBottom(pp, sym, maxY, onY2)
        top0 = symType.getEdgeTop(pp, sym, minY, onY2)
        top1 = symType.getEdgeTop(pp, sym, maxY, onY2)

        # baseline bars can flip order, so smallest x could be 'right', etc.
        xPxMin = min(min(left0, left1),
                            min(right0, right1))
        xPxMax = max(max(left0, left1),
                            max(right0, right1))
        yPxMin = min(min(bottom0, bottom1),
                            min(top0, top1))
        yPxMax = max(max(bottom0, bottom1),
                            max(top0, top1))
        result.x = xPxMin - extraSpace
        result.y = yPxMin - extraSpace
        result.width = xPxMax - xPxMin + 1 + 2*extraSpace
        result.height = yPxMax - yPxMin + 1 + 2*extraSpace

        # result is (roughly) smallest rectangle that contains every
        # rendered symbol on this curve (ignoring annotations)

        return result



    # keeps track of if last rendering was canvas-based or not
    def setWasCanvasRendered(self, wasCanvasRendered):
        self.wasCanvasRendered = wasCanvasRendered

    # is curve currently canvas rendered and up-to-date
    def isCanvasRendered(self):
        return self.validated  and  self.wasCanvasRendered


 # end of class Curve

