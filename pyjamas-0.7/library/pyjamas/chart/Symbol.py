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
import re

from pyjamas.ui.Widget import Widget

from pyjamas.chart import GChartConsts
from pyjamas.chart import Double
from pyjamas.chart import SymbolType
from pyjamas.chart import AnnotationLocation
from pyjamas.chart.Annotation import Annotation
from pyjamas.chart import HovertextChunk
from pyjamas.chart import GChartUtil

"""*
** Defines a chart curve symbol. Each point on a curve
** is represented on the chart by an appropriate
** rendering of the curve's symbol.
**
** @see Curve#getSymbol Curve.getSymbol
** @see SymbolType SymbolType
**
*"""

class Symbol(object):
    
    def __init__(self, parent):
        self.parent = parent
    
        self.annotation = None
        self.backgroundColor = GChartConsts.DEFAULT_SYMBOL_BACKGROUND_COLOR
        # same as backgroundColor, but with extended RGBA collapsed to plain RGA
        self.backgroundColorCSS = GChartConsts.DEFAULT_SYMBOL_BACKGROUND_COLOR
        self.baseline = Double.NaN
        self.borderColor = "black"
        self.borderColorCSS = "black"
        self.borderStyle = GChartConsts.DEFAULT_SYMBOL_BORDER_STYLE
        self.borderWidth = GChartConsts.DEFAULT_SYMBOL_BORDER_WIDTH
        self.brushHeight = GChartConsts.DEFAULT_BRUSH_HEIGHT
        self.brushLocation = AnnotationLocation.CENTER
        self.brushWidth = GChartConsts.DEFAULT_BRUSH_WIDTH
        self.fillHasHovertext = True
        self.fillSpacing = Double.NaN
        self.fillThickness = GChartConsts.NAI
        self.height = GChartConsts.DEFAULT_SYMBOL_HEIGHT
        self.hovertextTemplate=None
        # holds specification for the hover annotation. Actual
        # hover annotation is generated on the fly when they hover
        self.hoverAnnotation = None
        self.hoverAnnotationEnabled = True
        # allows hover annotation to use a different symbol type
        # than the symbol being hovered over. Main use expected to
        # be to place hover feedback at a fixed location on the chart (via
        # ANCHOR_* family of symbol types), for example, a status
        # bar message that changes depending on what the mouse
        # is touching.
        self.hoverAnnotationSymbolType = None
        # encloses each symbol in a 1 px gray selection rectangle:
        self.hoverSelectionBackgroundColor = "transparent"
        self.hoverSelectionBorderColor = "gray"
        self.hoverSelectionBorderStyle = "solid"
        self.hoverSelectionBorderWidth = -1
        self.hoverSelectionEnabled = True
        self.hoverSelectionFillSpacing = Double.NaN
        self.hoverSelectionFillThickness = GChartConsts.NAI
        self.hoverSelectionHeight = GChartConsts.NAI
        self.hoverSelectionImageURL = None
        self.hoverSelectionWidth = GChartConsts.NAI
        self.hoverSelectionSymbolType = None

        self.hovertextChunks = None
        self.imageURL = None
        # XXX: Symbols are used independently of Curves by the
        # realizeTick method. But it's probably better to render ticks
        # via specialized system curves. If/when that's implemented,
        # Symbol should become an inner class of Curve, and this
        # explicit parent pointer will no longer be required.

        # when specified, model width/height are in user-defined units.
        self.modelHeight = Double.NaN
        self.modelWidth = Double.NaN
        # NaN means "begin this slice where last slice left off, or at
        # initialPieSliceOrientation if it is the first slice to be rendered"
        self.pieSliceOrientation = Double.NaN
        self.defaultPieSliceOrientation = 0.0
        # slices, by default, fill the entire pie (useful for drawing disks)
        self.pieSliceSize = 1

        self.symbolType = SymbolType.DEFAULT_SYMBOL_TYPE

        self.width = GChartConsts.DEFAULT_SYMBOL_WIDTH
        self.xScaleFactor = 1.0
        self.yScaleFactor = 1.0
    
    
    """* Returns the CSS background color of all the rectangular
    ** elements used in rendering the symbol.
    **
    ** @return the CSS background color used to fill in the
    **  central (non-border) part of each rectangular element
    **  used to render a curve's symbol.
    **
    ** @see #setBackgroundColor(String) setBackgroundColor
    *"""
    def getBackgroundColor(self):
        return self.backgroundColor
    
    def getBackgroundColorCSS(self):
        return self.backgroundColorCSS
    
    """* Returns the baseline value for this symbol,
    ** previously specified via <tt>setBaseline</tt>
    **
    **
    ** @return the previously specified baseline value for
    **   this symbol.
    **
    ** @see #setBaseline setBaseline
    *"""
    def getBaseline(self):
        return self.baseline
    
    """* Returns the CSS border color of all the rectangular
    ** elements used in rendering the symbol.
    **
    ** <p>
    ** @return the color of the border of the rectangular elements
    **   used to render the symbol, in standard CSS format
    **
    ** @see #setBorderColor setBorderColor
    **
    *"""
    def getBorderColor(self):
        return self.borderColor
    
    def getBorderColorCSS(self):
        return self.borderColorCSS
    
    """*
    ** Returns the border style of all of the rectangular
    ** elements from which this symbol is built.
    ** <p>
    ** @return the CSS borderStyle of this symbol's elements
    **         (dotted, dashed, solid, etc. )
    **
    ** @see #setBorderStyle setBorderStyle
    *"""
    def getBorderStyle(self):
        return self.borderStyle
    
    
    """*
    ** Returns the width of the border around each
    ** rectangular element used to render this symbol,
    ** in pixels.
    **
    ** <p>
    ** @return the previously set border width (in pixels).
    **
    ** @see #setBorderWidth setBorderWidth
    """
    def getBorderWidth(self):
        return self.borderWidth
    
    """*
    *
    * Returns the height of the rectangular "brush" that defines
    * how close the mouse cursor must be to a rendered symbol for
    * the symbol to be considered to have been "touched" (which
    * causes the point's hover feedback to pop up).
    *
    * @return the height of the "brush", in pixels, associated
    * with this symbol/curve.
    *
    * @see #setBrushHeight setBrushHeight
    *
    """
    def getBrushHeight(self):
        return self.brushHeight
    
    
    """*
    *
    * Returns the location of the rectangular brush relative to
    * the current x,y coordinates of the mouse cursor.
    * <p>
    *
    * @return the location of the rectangular brush relative to
    * the x,y coordinates of the mouse cursor.
    *
    * @see #setBrushLocation setBrushLocation
    """
    def getBrushLocation(self):
        return self.brushLocation
    
    
    
    """*
    *
    * Returns the width of the rectangular "brush" that defines
    * how close the mouse cursor must be to a rendered symbol for
    * the symbol to be considered to have been "touched" (which
    * causes the point's hover feedback to pop up).  <p>
    *
    * @return the width of the "brush", in pixels, associated
    *   with this symbol/curve.
    *
    * @see #setBrushWidth setBrushWidth
    *
    """
    def getBrushWidth(self):
        return self.brushWidth
    
    
    """*
    ** @deprecated
    **
    ** Returns the value previously set by setFillHasHovertext.
    **
    ** @see #setFillHasHovertext setFillHasHovertext
    **
    *"""
    def getFillHasHovertext(self):
        return self.fillHasHovertext
    
    
    
    """*
    ** Returns the spacing between successive rectangular
    ** elements used to emulate any required non-rectangular
    ** features of the symbol.  <p>
    **
    **
    **
    ** @return the previously set (or the default, if the
    ** fillSpacing has been set to <tt>Double.NaN</tt>) fill spacing
    ** (in pixels).
    **
    ** @see #setFillSpacing setFillSpacing
    ** @see #setFillThickness setFillThickness
    **
    """
    def getFillSpacing(self):
        if Double.NaN==(self.fillSpacing):
            return self.symbolType.defaultFillSpacing()
        
        else:
            return self.fillSpacing
        
    
    
    """*
    ** Returns the "thickness" of rectangular elements used to
    ** emulate any required non-rectangular features of the symbol.
    ** <p>
    **
    **
    ** @return the previously set (or the default, if the
    ** fillThickness has been set to <tt>GChartConsts.NAI</tt>) fill
    ** thickness (in pixels).
    **
    ** @see #setFillThickness setFillThickness
    ** @see #setFillSpacing setFillSpacing
    """
    def getFillThickness(self):
        if self.fillThickness==GChartConsts.NAI:
            return self.symbolType.defaultFillThickness()
        
        else:
            return self.fillThickness
        
    
    
    """ Retrieves the annotation that defines the properties of
    * the internally generated annotations used to display
    * hover feedback. """
    def getHoverAnnotation(self):
        if self.hoverAnnotation is None:
            self.hoverAnnotation = Annotation()
        
        return self.hoverAnnotation
    
    """*
    * Retrieves a boolean that indicates if point-specific
    * annotations popup whenever you hover over a point on the
    * curve associated with this symbol.<p>
    *
    * @return True if hover-induced annotations popup, False otherwise.
    *
    * @see #setHoverAnnotationEnabled setHoverAnnotationEnabled
    *
    """
    def getHoverAnnotationEnabled(self):
        return self.hoverAnnotationEnabled
    
    """*
    ** Retrieves the weight of the font that will be used
    ** with this symbol's hover annotations.
    ** <p>
    **
    ** @return the standard CSS font-weight
    **    specification such as normal, bold, bolder, lighter,
    **    100, 200, ... 900, or inherit used by hover
    **    annotations
    **
    ** @see #setHoverFontWeight setHoverFontWeight
    **
    **
    *"""
    def getHoverFontWeight(self):
        result = self.getHoverAnnotation().getFontWeight()
        return result
    
    """*
    ** Retrieves the font color of this symbol's hover
    ** annotations.
    **
    ** @return color of the font used to display this
    **    symbol's hover annotations
    **
    ** @see #setHoverFontColor setHoverFontColor
    *"""
    def getHoverFontColor(self):
        result = self.getHoverAnnotation().getFontColor()
        return result
    
    
    
    """*
    ** Retrieves the CSS font-style used with this symbol's
    ** hover annotations.
    **
    ** @return the CSS font-style, namely,
    **   normal, italic, oblique, or inherit of text displayed
    **   in the hover annotations associated with this symbol
    **
    ** @see #setHoverFontStyle setHoverFontStyle
    *"""
    def getHoverFontStyle(self):
        result = self.getHoverAnnotation().getFontStyle()
        return result
    
    """*
    ** Retrieves the CSS font size used with this symbol's hover
    ** annotations, in pixels.
    **
    ** @return the font size used in the text displayed
    ** in the hover annotations associated with this symbol.
    **
    ** @see #setHoverFontSize setHoverFontSize
    **
    *"""
    def getHoverFontSize(self):
        result = self.getHoverAnnotation().getFontSize()
        return result
    
    
    """*
    * Retrieves point-relative location of this symbol's hover
    * annotations.  <p>
    *
    * @return the relative location of the hover annotations for
    * all points on the curve associated with this symbol.
    *
    * @see #setHoverLocation setHoverLocation
    * @see #DEFAULT_HOVER_LOCATION DEFAULT_HOVER_LOCATION
    *
    """
    def getHoverLocation(self):
        result = self.getHoverAnnotation().getLocation()
        if None == result:
            result = self.getSymbolType().defaultHoverLocation()
        
        return result
    
    """*
    * Retrieves the symbol type that will determine how the
    * hover annotations for this symbol gets positioned.
    * <p>
    *
    * @return <tt>SymbolType</tt> used to position hover
    * annotations, or <tt>None</tt> if the symbol type of the
    * hovered over point is being used.
    *
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    *
    """
    def getHoverAnnotationSymbolType(self):
        return self.hoverAnnotationSymbolType
    
    """*
    * Retrieves the background color used to indicate that the mouse is
    * "touching" (hovering over) a point.
    *
    * @return a CSS color specification string that represents
    * the background color used to indicate "hover-selection".
    *
    * @see #setHoverSelectionBackgroundColor
    * setHoverSelectionBackgroundColor
    """
    def getHoverSelectionBackgroundColor(self):
        return self.hoverSelectionBackgroundColor
    
    """*
    * Retrieves the border color used to indicate that the mouse is
    * "touching" (hovering over) a point.
    *
    * @return a CSS color specification string that represents
    * the border color used to indicate "hover-selection".
    *
    * @see #setHoverSelectionBorderColor
    * setHoverSelectionBorderColor
    """
    def getHoverSelectionBorderColor(self):
        return self.hoverSelectionBorderColor
    
    """*
    * Retrieves the border style used to indicate that the mouse is
    * "touching" (hovering over) a point.
    *
    * @return a CSS border style specification string that represents
    * the border style used to indicate "hover-selection".
    *
    * @see #setHoverSelectionBorderStyle
    * setHoverSelectionBorderStyle
    """
    def getHoverSelectionBorderStyle(self):
        return self.hoverSelectionBorderStyle
    
    """*
    * Retrieves the width of the border around the perimeter of
    * rectangles used to indicate that the mouse is
    * "touching" (hovering over) a point.
    * <p>
    *
    *
    * @return the width of the border drawn around the perimeter of
    * the selected symbol's rectangles to indicate that it has
    * been "touched: by the mouse.
    *
    * @see #setHoverSelectionBorderWidth
    * setHoverSelectionBorderWidth
    """
    def getHoverSelectionBorderWidth(self):
        return self.hoverSelectionBorderWidth
    
    """*
    * Retrieves a boolean that indicates if hover selection
    * feedback will be provided for this curve.  <p>
    *
    * @return if True, hover selection feedback is enabled,
    *   if False, hovering over a point does not change its
    *   color.
    *
    * @see #setHoverSelectionEnabled setHoverSelectionEnabled
    *
    """
    def getHoverSelectionEnabled(self):
        return self.hoverSelectionEnabled
    
    
    """*
    * Returns the fill spacing that will be used when
    * rendering this curve's hover selection feedback.
    * <p>
    *
    * @return fill spacing used by hover selection feedback,
    * or <tt>GChartConsts.NAI</tt> if the fill spacing setting
    * of the hovered-over curve is to be used.
    *
    * @see #setHoverSelectionFillSpacing
    *   setHoverSelectionFillSpacing
    *
    """
    def getHoverSelectionFillSpacing(self):
        return self.hoverSelectionFillSpacing
    
    """*
    * Returns the fill thickness that will be used when
    * rendering this curve's hover selection feedback.
    * <p>
    *
    * @return fill thickness used by hover selection feedback,
    * or <tt>GChartConsts.NAI</tt> if the fill thickness setting
    * of the hovered-over curve is to be used.
    *
    * @see #setHoverSelectionFillThickness
    *       setHoverSelectionFillThickness
    *
    """
    def getHoverSelectionFillThickness(self):
        return self.hoverSelectionFillThickness
    
    
    """*
    * Returns the height of the symbol used to indicate
    * when a given point is being "hovered over" with the
    * mouse.
    * <p>
    *
    * @return the height of the symbol used to
    * indicate that that a point has been selected, or
    * <tt>GChartConsts.NAI</tt> if the the height of the
    * symbol representing the selected point is being used.
    *
    *
    * @see #setHoverSelectionHeight setHoverSelectionHeight
    *
    """
    def getHoverSelectionHeight(self):
        return self.hoverSelectionHeight
    
    
    """*
    * Returns the URL that will be used for all of the
    * images used in rendering this symbol's selection feedback.
    * <p>
    *
    * @see #setHoverSelectionImageURL
    *
    * @return the url that defines the <tt>src</tt> property of all
    * images used to draw this the selection feedback associated
    * with this symbol.
    *
    """
    
    def getHoverSelectionImageURL(self):
        if self.hoverSelectionImageURL:
            return self.hoverSelectionImageURL
        return self.parent.chart.getBlankImageURL()
    
    
    
    """*
    *
    * Returns the symbol type that GChart will use when generating
    * selection feedback. GChart indicates that a point is
    * selected by re-rendering the point as if it had this symbol
    * type.
    *
    *
    * @return the symbol type that in
    * part determines how selection feedback for a hovered over
    * point is drawn, or <tt>None</tt> if defaulting to the
    * symbol type of the hovered over point.
    *
    * @see #setHoverSelectionSymbolType setHoverSelectionSymbolType
    *
    """
    def getHoverSelectionSymbolType(self):
        return self.hoverSelectionSymbolType
    
    """*
    * Returns the width of the symbol used to indicate
    * when a given point is being "hovered over" with the
    * mouse.
    * <p>
    *
    * @return the width of the symbol used to indicate that
    * that a point has been selected, or <tt>GChartConsts.NAI</tt> if
    * using to the width of the symbol representing the
    * selected point.
    *
    *
    * @see #setHoverSelectionWidth setHoverSelectionWidth
    *
    *
    """
    def getHoverSelectionWidth(self):
        return self.hoverSelectionWidth
    
    
    """*
    ** Returns the hovertextTemplate of this symbol.
    ** <p>
    **
    ** @return hovertextTemplate of the symbol
    **
    **
    ** @see #setHovertextTemplate(String) setHovertextTemplate
    **
    *"""
    def getHovertextTemplate(self):
        if None == self.hovertextTemplate:
            return self.symbolType.defaultHovertextTemplate()
        
        else:
            return self.hovertextTemplate
        
    
    
    """*
    * When widget-based hover annotations are being used
    * by the curve associated with this symbol, this method returns
    * the <tt>HoverUpdateable</tt> widget used within
    * those annotations. When simple text or HTML hover
    * annotations are being used, it returns None.
    *
    * @return the widget used to provide widget-based hover
    * annotations or None if hover annotations are not
    * widget-based.
    *
    * @see #setHoverWidget setHoverWidget
    *
    """
    def getHoverWidget(self):
        return self.getHoverAnnotation().getWidget()
    
    
    
    
    
    """*
    * Retrieves the number of pixels (along the x-axis) that
    * this point's hover-annotation will be moved from its default,
    * <tt>setHoverLocation</tt>-defined, point-relative location.
    * <p>
    *
    * @return x-shift, in pixels, of the hover annotation
    *
    * @see #setHoverXShift getHoverXShift
    *
    """
    def getHoverXShift(self):
        result = self.getHoverAnnotation().getXShift()
        return result
    
    
    """*
    * Retrieves the number of pixels (along the y-axis) that
    * this point's hover annotation will be moved from its default,
    * <tt>setHoverLocation</tt>-defined, point-relative location.
    * <p>
    *
    * @return y-shift, in pixels, of the hover annotation
    *
    * @see #setHoverYShift setHoverYShift
    *
    """
    def getHoverYShift(self):
        result = self.getHoverAnnotation().getYShift()
        return result
    
    
    """*
    * Returns the URL that will be used for all of the
    * images used in rendering this symbol.
    * <p>
    *
    * @see #setImageURL setImageURL
    * @see #setBlankImageURL setBlankImageURL
    *
    * @return the url that defines the <tt>src</tt> property of all
    * images used to draw this symbol on the chart.
    """
    def getImageURL(self):
        if self.imageURL:
            return self.imageURL
        return self.parent.chart.getBlankImageURL()
    
    # returns an internal, parsed form of the hovertext template
    def getHovertextChunks(self):
        if None == self.hovertextChunks:
            self.hovertextChunks = HovertextChunk.parseHovertextTemplate(
                                            self.getHovertextTemplate())
        
        return self.hovertextChunks
    
    
    """* Returns the <tt>GChart</tt> that contains this
    ** <tt>Symbol</tt>.
    **
    ** @return a reference to the <tt>GChart</tt> that
    **   contains this <tt>Symbol</tt> (its "parent")
    **
    *"""
    def getChart(self):
        return self.parent.chart
    
    """* Returns the <tt>Curve</tt> that contains this
    ** <tt>Symbol</tt>.
    **
    ** @return a reference to the <tt>Curve</tt> that
    **   contains this <tt>Symbol</tt> (its "parent")
    **
    *"""
    def getParent(self):
        return self.parent
    
    """*
    ** Returns the value, previously specified via
    ** <tt>setPieSliceOrientation</tt>, that defines the angular
    ** orientation of any pie slices associated with this
    ** symbol.  <p>
    **
    **
    ** @return the value, either <tt>Double.NaN</tt> or a value
    **         between 0 and 1 previously set via
    **         <tt>setPieSliceOrientation</tt>, that determines the
    **         angular orientation of any pie slice associated
    **         with this symbol.
    **
    ** @see #setPieSliceOrientation setPieSliceOrientation
    ** @see #setPieSliceSize setPieSliceSize
    **
    """
    def getPieSliceOrientation(self):
        return self.pieSliceOrientation
    
    # Used internally to translate <tt>Double.NaN</tt> into
    # an appropriate default slice orientation that, when pie
    # slice orientation isn't explicitly specified, results
    # in a series of adjacent slices that will form a pie
    # when the sum of the slice sizes equals 1.0
    
    def getDecodedPieSliceOrientation(self):
        result = self.pieSliceOrientation
        if (Double.NaN==(result)):
            result = self.defaultPieSliceOrientation
        
        return result
    
    
    def setDefaultPieSliceOrientation(self, defaultOrientation):
        self.defaultPieSliceOrientation = defaultOrientation
    
    def getDefaultPieSliceOrientation(self):
        return self.defaultPieSliceOrientation
    
    
    """*
    ** Returns the value, previously specified via
    ** <tt>setPieSliceSize</tt>, that defines the size of
    ** the angle subtended by any pie slice associated with this
    ** symbol.  <p>
    **
    ** @return the value, between 0 and 1 and previously set via
    **         <tt>setPieSliceSize</tt>, that defines the
    **         size of the "wedge of pie" as a fraction of
    **         the total pie, for any pie slice associated
    **         with this symbol.
    **
    ** @see #setPieSliceOrientation setPieSliceOrientation
    ** @see #setPieSliceSize setPieSliceSize
    **
    """
    def getPieSliceSize(self):
        return self.pieSliceSize
    
    
    
    """
    * Returns the radius of the pie from which this
    * symbol's pie slice was extracted.
    *
    """
    def getPieSliceRadius(self, pp, onY2):
        w = self.getWidth(pp);      # needed to decode model
        h = self.getHeight(pp,onY2);# width,height into pixels
        result = math.sqrt(w*w + h*h)/2.
        # Tweak radius to assure it is an even multiple of the fill
        # spacing. Makes it possible to assure regular band spacing
        # across pie at the expense of less precise control of pie
        # size (regular band spacing makes it look much better).
        spacing = self.getFillSpacing()
        if 0 == spacing:
            spacing = 1
        
        nBands = int ( round(result/spacing) )
        result = nBands * spacing
        return result
    
    
    # defines first, second edge angle in standard radian units
    def getPieSliceTheta0(self):
        
        result = (0.75 - self.getDecodedPieSliceOrientation())*2*math.pi
        return result
    
    def getPieSliceTheta1(self):
        return self.getPieSliceTheta0() - 2.*math.pi*self.getPieSliceSize()
    
    
    """*
    ** Returns this symbol's height as previously set by
    ** <tt>setModelHeight</tt>.
    **
    ** @return the previously set symbol height, in model units
    **
    ** @see #setModelHeight setModelHeight
    ** @see #setModelWidth setWidth
    ** @see #setHeight setHeight
    ** @see #setWidth setWidth
    **
    """
    def getModelHeight(self):
        return self.modelHeight
    
    
    
    """*
    ** Returns this symbol's width as previously set by
    ** <tt>setModelWidth</tt>.
    **
    ** @return the previously set symbol width, in model units.
    **
    ** @see #setModelWidth setModelWidth
    ** @see #setModelHeight setModelHeight
    ** @see #setWidth setWidth
    ** @see #setHeight setHeight
    **
    """
    def getModelWidth(self):
        return self.modelWidth
    
    """* Returns this symbol's type.
    **
    ** @return the type of this symbol.
    ** @see #setSymbolType setSymbolType
    **
    *"""
    def getSymbolType(self):
        return self.symbolType
    
    """
    * Do points on the curve associated with this symbol
    * use a horizontal (or vertical) binning strategy for
    * "what point is the mouse over" hit testing?
    *
    """
    def isHorizontallyBanded(self):
        if None == self.symbolType.horizontallyBanded:
            # not fixed by symbol type: use brush shape determined banding
            # (we are guessing point distribution based on brush shape)
            result = self.brushHeight < self.brushWidth
        
        else:
            result = bool(self.symbolType.isHorizontallyBanded())
        
        
        return result
    
    
    
    """
    * If passed an rgba-like string (rgba(255,255,128,0.5))
    * returns the collapsed-to-rgb version (rgb(255,255,128)).
    * Else returns the original string. Throws an exception
    * if string begins with rgba( but lacks required
    * format after that.
    *
    """
    def collapseRGBAToRGB(self, rgba):
        # an int in the range 0..255 for the "R,G,B" parts
        RGB = "([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|(25[0-5]))"
        # a double in the range 0..1 for the "A" part
        A = "(0|1|(1[.]0*)|(0[.][0-9]*)|([.][0-9]+))"
        # full RGBA pattern
        RGBA_PATTERN = \
                "rgba[(]" + RGB + "[,]" + RGB + "[,]" + RGB + "[,]" + A + "[)]"
        result = rgba
        if None != rgba  and  rgba.startswith("rgba("):
            rp = re.compile(RGBA_PATTERN)
            if rp.match(rgba):
                FIRST_PAREN = 4
                lastComma = rgba.rfind(",")
                result = "rgb" + rgba[FIRST_PAREN:lastComma] + ")"
            
            else:
                raise IllegalArgumentException(
                "Your RGBA color specification: '" + rgba + "'" +
                " was not in the GChart-required form: rgba(Red,Green,Blue,Alpha)" +
                " where Red, Green and Blue are integers in the range 0 to 255 and" +
                " Alpha is a double in the range 0.0 to 1.0")
            
        
        # else special keyword or else some (unchecked) CSS color format
        return result
    
    
    """*
    ** Specifies the background or fill color of this symbol.

    ** @param backgroundColor a standard CSS or canvas-library
    ** supported RGBA background color specification string.
    **
    **
    ** @see #getBackgroundColor getBackgroundColor
    ** @see #setBorderColor setBorderColor
    ** @see #DEFAULT_SYMBOL_BACKGROUND_COLOR DEFAULT_SYMBOL_BACKGROUND_COLOR
    ** @see #setImageURL setImageURL
    **
    *"""
    def setBackgroundColor(self, backgroundColor):
        self.getParent().invalidate()
        self.backgroundColor = backgroundColor
        # don't want to keep collapsing whenever we render, so save it:
        self.backgroundColorCSS = self.collapseRGBAToRGB(backgroundColor)
    
    
    """* Specifies the baseline value for this symbol. Use a
    ** baseline value when you need to create bar charts whose
    ** bars extend up/down to a specified y baseline value (for
    ** vertical bar charts) or left/right to a specified x baseline
    ** value (for horizontal bar charts).
    **
    ** @param baseline the y (or x) that defines the horizontal
    **   (or vertical) line to which any baseline-based vertical
    **   (or horizontal) bars are extended.
    **
    ** @see #getBaseline getBaseline
    ** @see SymbolType#HBAR_BASELINE_CENTER HBAR_BASELINE_CENTER
    ** @see SymbolType#HBAR_BASELINE_SOUTH HBAR_BASELINE_SOUTH
    ** @see SymbolType#HBAR_BASELINE_NORTH HBAR_BASELINE_NORTH
    ** @see SymbolType#VBAR_BASELINE_CENTER VBAR_BASELINE_CENTER
    ** @see SymbolType#VBAR_BASELINE_EAST VBAR_BASELINE_EAST
    ** @see SymbolType#VBAR_BASELINE_WEST VBAR_BASELINE_WEST
    **
    *"""
    def setBaseline(self, baseline):
        self.getParent().invalidate()
        self.baseline = baseline
    
    
    
    """*
    ** Specifies the border color, as a CSS or RGBA color
    ** specification string.
    **
    ** @param borderColor the color of the borders of this curve's rendered
    ** symbols, and of any point-to-point connecting lines. Use any
    ** valid CSS color specification string (including the
    ** RGBA extension), or the special
    ** GChart keyword <tt>TRANSPARENT_BORDER_COLOR</tt>.
    **
    ** For more information on standard CSS color specifications
    ** including
    ** how GChart handles the RGBA extended format, see
    ** {@link Symbol#setBackgroundColor setBackgroundColor}.
    **
    ** @see #TRANSPARENT_BORDER_COLOR TRANSPARENT_BORDER_COLOR
    ** @see #getBorderColor getBorderColor
    ** @see #setBackgroundColor setBackgroundColor
    ** @see #setCanvasFactory setCanvasFactory
    **
    *"""
    def setBorderColor(self, borderColor):
        self.getParent().invalidate()
        self.borderColor = borderColor
        self.borderColorCSS = self.collapseRGBAToRGB(borderColor)
    
    
    """*
    ** Sets the border style of the rectangular elements used
    ** to render this symbol.
    **
    ** <p>
    **
    ** <p>
    ** @param borderStyle a CSS border style such as
    ** "solid", "dotted", "dashed", etc.
    **
    ** @see #getBorderStyle getBorderStyle
    ** @see #setBackgroundColor setBackgroundColor
    ** @see #setBorderColor setBorderColor
    *"""
    def setBorderStyle(self, borderStyle):
        self.getParent().invalidate()
        self.borderStyle = borderStyle
    
    """*
    ** Sets the width of the border around the graphical
    ** element(s) used to render this curve, in pixels.
    **
    ** @param borderWidth the width of the symbol's border, in pixels
    ** @see #getBorderWidth getBorderWidth
    *"""
    def setBorderWidth(self, borderWidth):
        self.getParent().invalidate()
        self.borderWidth = borderWidth
    
    
    """*
    *
    * Sets the height of the rectangular point-selection
    * "brush". This brush defines how close the mouse
    * must get to a point on the chart in order to "touch" it.
    *
    * @param height the height of the rectangular point
    * selection brush used by points on the curve associated
    * with this symbol (in pixels).
    *
    * @see #getBrushHeight getBrushHeight
    * @see #setBrushWidth setBrushWidth
    * @see #setBrushSize setBrushSize
    * @see #setBrushLocation setBrushLocation
    * @see #setDistanceMetric setDistanceMetric
    * @see Symbol#setHoverWidget setHoverWidget
    * @see HoverUpdateable HoverUpdateable
    * @see #DEFAULT_BRUSH_WIDTH DEFAULT_BRUSH_WIDTH
    * @see #DEFAULT_BRUSH_HEIGHT DEFAULT_BRUSH_HEIGHT
    * @see #getTouchedPoint getTouchedPoint
    * @see #touch touch
    * @see GChart#setHoverTouchingEnabled setHoverTouchingEnabled
    *
    """
    def setBrushHeight(self, height):
        self.brushHeight = height
    
    
    """*
    * Sets the location of the brush relative to the mouse
    * x,y coordinates.
    *
    * @see #setBrushHeight setBrushHeight
    * @see #setBrushWidth setBrushWidth
    * @see GChart#getYChartSizeDecorated getYChartSizeDecorated
    *
    * @param location the location of the rectangular brush,
    * relative to the x,y position of the mouse.
    *
    """
    def setBrushLocation(self, location):
        self.brushLocation = location
    
    
    
    
    """*
    *
    * Convenience method equivalent to:
    * <p>
    *
    * <pre>
    *   setBrushWidth(width)
    *   setBrushHeight(height)
    * </pre>
    *
    * <p>
    * For a full discussion of how GChart uses its "brush" to
    * determine when hover feedback for a point gets displayed,
    * see <tt>setBrushHeight</tt>.
    * <p>
    *
    * @param width the width of this chart's brush, in pixels
    * @param height the height of this chart's brush, in pixels
    *
    *
    * @see #setBrushHeight setBrushHeight
    * @see #setBrushWidth setBrushWidth
    * @see #DEFAULT_BRUSH_WIDTH DEFAULT_BRUSH_WIDTH
    * @see #DEFAULT_BRUSH_HEIGHT DEFAULT_BRUSH_HEIGHT
    *
    * <p>
    *
    *
    """
    def setBrushSize(self, width, height):
        self.setBrushWidth(width)
        self.setBrushHeight(height)
    
    
    
    
    """*
    *
    * Sets the width of the rectangular "brush" that defines how
    * close the mouse position must be to a rendered symbol for
    * that symbol to have been "touched".
    * <p>
    *
    * For a full discussion of how GChart uses it's "brush" to
    * determine when hover feedback for a point gets displayed,
    * see <tt>setBrushHeight</tt>.
    *
    * @param width width of the point selection brush, in pixels.
    *
    * @see #setBrushHeight setBrushHeight
    * @see #setBrushSize setBrushSize
    * @see #DEFAULT_BRUSH_WIDTH DEFAULT_BRUSH_WIDTH
    * @see #DEFAULT_BRUSH_HEIGHT DEFAULT_BRUSH_HEIGHT
    *
    *
    """
    def setBrushWidth(self, width):
        self.brushWidth = width
    
    
    
    """*
    *
    * Allows you to change the x,y scale factors that define
    * the distance between the mouse cursor and each
    * rendered point; these distances determine which point is
    * "closest" to the mouse during hit testing.  <p>
    *
    * @param xScaleFactor multiplies the x-pixel distance
    * between the mouse cursor and the point center (see
    * distance formula above).
    * @param yScaleFactor multiplies the y-pixel distance
    * between the mouse cursor and the point center (see
    * distance formula above).
    *
    * @see #setBrushSize setBrushSize
    * @see #setBrushLocation setBrushLocation
    * @see #setHoverSelectionEnabled setHoverSelectionEnabled
    * @see #setHoverAnnotationEnabled setHoverAnnotationEnabled
    *
    """
    def setDistanceMetric(self, xScaleFactor, yScaleFactor):
        self.xScaleFactor = xScaleFactor
        self.yScaleFactor = yScaleFactor
    
    
    """*
    ** @deprecated
    **
    ** As of GChart 2.4, hover feedback has been completely
    ** redesigned. Though these changes are mostly positive,
    ** one downside is that, to simplify its hit-testing
    ** algorithms, GChart only provides hover feedback for the
    ** explicitly specified data points on a line chart; it can
    ** no longer provide feedback for the "filled in" points
    ** connecting successive data points.  If you need hover
    ** feedback on such interpolated points you will have to
    ** explicitly add individual data points to the curve
    ** representing the interpolated values.  <p>
    **
    ** Another difference is that you can no longer turn off
    ** hover feedback for a pie slice via this method. If you
    ** need to turn hover feedback off for a pie slice (or for
    ** any other symbol, for that matter) you can use the
    ** (with 2.4) <tt>setHoverAnnotationEnabled</tt> and
    ** <tt>setHoverSelectionEnabled</tt> methods.
    **
    **
    ** @see #getFillHasHovertext getFillHasHovertext
    ** @see #setHovertextTemplate setHovertextTemplate
    ** @see #setBrushSize setBrushSize
    ** @see #setHoverAnnotationEnabled setHoverAnnotationEnabled
    ** @see #setHoverSelectionEnabled setHoverSelectionEnabled
    **
    *"""
    def setFillHasHovertext(self, fillHasHovertext):
        self.fillHasHovertext = fillHasHovertext
    
    
    """*
    ** Specifies the spacing between successive rectangular
    ** elements used to render any required non-rectangular
    ** features of the symbol.  <p>
    **
    ** The exact meaning of this spacing
    ** setting depends on the symbol type, and on if an external
    ** canvas factory has been specified via
    ** <tt>setCanvasFactory</tt>:
    **
    ** <p>
    **
    ** @param fillSpacing spacing between successive rectangular
    **   elements used to fill in non-rectangular symbols, in
    **   pixels. If a canvas factory has been specified,
    **   you can use a setting of <tt>0</tt> to produces
    **   "continuously filled" elements.
    **
    **
    ** @see #getFillSpacing getFillSpacing
    ** @see #setFillThickness setFillThickness
    ** @see #setCanvasFactory setCanvasFactory
    **
    """
    def setFillSpacing(self, fillSpacing):
        self.getParent().invalidate()
        if (not (Double.NaN==(fillSpacing))  and  
            fillSpacing != 0  and  fillSpacing < 1):
            raise IllegalArgumentException(
            "fillSpacing="+fillSpacing+"; "+
            "fillSpacing must either be >= 1, or else " +
            "equal to either 0 or Double.NaN.")
        
        self.fillSpacing = fillSpacing
    
    
    """*
    ** Sets the "thickness" of the rectangular elements used to
    ** render any required non-rectangular features of this symbol.
    ** <p>
    **
    ** The exact meaning of this thickness setting, as well as
    ** the default used whenever the thickness is set to the
    ** special undefined integer value recognized by GChart
    ** (<tt>GChartConsts.NAI</tt>), depends on the symbol type, and
    ** if an external canvas factory has been specified via
    ** <tt>setCanvasFactory</tt>:
    ** <p>
    **
    ** @param fillThickness the fill thickness, in pixels
    **
    ** @see #setCanvasFactory setCanvasFactory
    ** @see #getFillThickness getFillThickness
    ** @see #setFillSpacing setFillSpacing
    """
    def setFillThickness(self, fillThickness):
        self.getParent().invalidate()
        if fillThickness!=GChartConsts.NAI  and  fillThickness < 0:
            raise IllegalArgumentException(
            "fillThickness="+self.fillThickness+"; "+
            "fillThickness must either be >= 0, or else " +
            "equal to GChartConsts.NAI.")
        
        self.fillThickness = fillThickness
    
    
    """*
    * Sets a boolean that determines if point-specific
    * annotations will popup whenever you hover over a point on
    * the curve associated with this symbol.<p>
    *
    * By default, these hover-induced popups are enabled.
    * <p>
    *
    * Note that the point selection feedback on the
    * hovered-over point is controlled separately, via the
    * <tt>setHoverSelectionEnabled</tt> method.
    *
    * @param hoverAnnotationEnabled True if hover-induced annotations popup on this
    * curve, False otherwise.
    *
    * @see #getHoverAnnotationEnabled getHoverAnnotationEnabled
    * @see #setHoverSelectionEnabled setHoverSelectionEnabled
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverWidget setHoverWidget
    * @see #setHoverLocation setHoverLocation
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    * @see #setHoverXShift setHoverXShift
    * @see #setHoverYShift setHoverYShift
    *
    """
    def setHoverAnnotationEnabled(self, hoverAnnotationEnabled):
        self.hoverAnnotationEnabled = hoverAnnotationEnabled
    
    """*
    ** Specifies the weight of the font that will be used
    ** to render the text of this point's hover annotations.
    ** <p>
    **
    ** @param cssWeight A standard CSS font-weight
    **    specification such as normal, bold, bolder, lighter,
    **    100, 200, ... 900, or inherit
    **
    ** @see #getHoverFontWeight getHoverFontWeight
    ** @see #setHoverFontColor setHoverFontColor
    ** @see #setHoverFontStyle setHoverFontStyle
    ** @see #setHoverFontSize setHoverFontSize
    ** @see #setHoverLocation setHoverLocation
    ** @see #setHoverWidget setHoverWidget
    ** @see #setHoverXShift setHoverXShift
    ** @see #setHoverYShift setHoverYShift
    **
    **
    **
    *"""
    def setHoverFontWeight(self, cssWeight):
        self.getHoverAnnotation().setFontWeight(cssWeight)
    
    """*
    ** Specifies the color of the hover annotations' font.
    **
    **
    ** <p>
    ** For more information on standard CSS color
    ** specifications see the discussion in
    ** {@link Symbol#setBackgroundColor Symbol.setBackgroundColor}.
    ** <p>
    **
    ** @param cssColor color of the font used to display this
    **    symbol's hover annotations.
    **
    ** @see #getHoverFontColor getHoverFontColor
    ** @see #setHoverFontWeight setHoverFontWeight
    ** @see #setHoverFontStyle setHoverFontStyle
    ** @see #setHoverFontSize setHoverFontSize
    ** @see #setHoverLocation setHoverLocation
    ** @see #setHoverWidget setHoverWidget
    ** @see #setHoverXShift setHoverXShift
    ** @see #setHoverYShift setHoverYShift
    *"""
    def setHoverFontColor(self, cssColor):
        self.getHoverAnnotation().setFontColor(cssColor)
    
    
    
    """*
    ** Specifies the CSS font-style used by this symbol's hover
    ** annotations.
    **
    ** @param cssStyle any valid CSS font-style, namely,
    **   normal, italic, oblique, or inherit.
    **
    ** @see #getHoverFontStyle getHoverFontStyle
    ** @see #setHoverFontWeight setHoverFontWeight
    ** @see #setHoverFontColor setHoverFontColor
    ** @see #setHoverFontSize setHoverFontSize
    ** @see #setHoverLocation setHoverLocation
    ** @see #setHoverWidget setHoverWidget
    ** @see #setHoverXShift setHoverXShift
    ** @see #setHoverYShift setHoverYShift
    *"""
    def setHoverFontStyle(self, cssStyle):
        self.getHoverAnnotation().setFontStyle(cssStyle)
    
    """*
    ** Specifies the CSS font size used in this symbol's hover
    ** annotations, in pixels.
    **
    ** @param fontSize the CSS font size used in the
    ** hover annotations associated with this symbol, in pixels.
    **
    ** @see #getHoverFontSize getHoverFontSize
    ** @see #setHoverFontWeight setHoverFontWeight
    ** @see #setHoverFontColor setHoverFontColor
    ** @see #setHoverFontStyle setHoverFontStyle
    ** @see #setHoverLocation setHoverLocation
    ** @see #setHoverWidget setHoverWidget
    ** @see #setHoverXShift setHoverXShift
    ** @see #setHoverYShift setHoverYShift
    *"""
    def setHoverFontSize(self, fontSize):
        self.getHoverAnnotation().setFontSize(fontSize)
    
    """*
    *
    * Specifies the location of this point's hover annotations. Set
    * this property to <tt>None</tt> (the default) to use GChart's
    * default hover location, which varies with the hover annotation's
    * symbol type, as tabulated below. (The hover annotation symbol type defaults to the
    * symbol type of the hovered over curve, and can be specified
    * explicitly via the <tt>setHoverAnnotationSymbolType</tt> method).
    * <p>
    *
    * <table border>
    *   <tr><th>SymbolType used to<br>position hover annotation</th>
    *   <th>Default Hover<br>AnnotationLocation</th></tr>
    *   <tr><td>HBAR_BASELINE_*</td><td>FARTHEST_FROM_VERTICAL_BASELINE</td></tr>
    *   <tr><td>HBAR_*WEST</td><td>EAST</td></tr>
    *   <tr><td>HBAR_*EAST</td><td>WEST</td></tr>
    *   <tr><td>PIE_SLICE_*</td><td>OUTSIDE_PIE_ARC</td></tr>
    *   <tr><td>VBAR_SOUTH*</td><td>NORTH</td></tr>
    *   <tr><td>VBAR_BASELINE_*</td><td>FARTHEST_FROM_HORIZONTAL_BASELINE</td></tr>
    *   <tr><td>VBAR_NORTH*</td><td>SOUTH</td></tr>
    *   <tr><td>All others</td><td>NORTHWEST</td></tr>
    * </table>
    *
    * <p>
    *
    * You can further adjust the position of a point's
    * hover annotations by specifying non-zero positional shifts via
    * the <tt>setHoverXShift</tt> and
    * <tt>setHoverYShift</tt> methods, and via the
    * <tt>setHoverAnnotationSymbolType</tt> method.
    * <p>
    *
    * <i>Tip:</i> To position hover annotations at a fixed location
    * on the chart, (such as a status bar that displays
    * information about the hovered over point, an inset chart
    * that shows a detailed view, etc.)  pass one of the
    * <tt>ANCHOR_*</tt> symbol types to the
    * <tt>setHoverAnnotationSymbolType</tt> method.  <p>
    *
    * @param hoverLocation the relative location of
    * the hover annotations, or <tt>None</tt> to use a
    * symbol-type-specific default.
    *
    * @see #getHoverLocation getHoverLocation
    * @see #setHoverFontWeight setHoverFontWeight
    * @see #setHoverFontColor setHoverFontColor
    * @see #setHoverFontStyle setHoverFontStyle
    * @see #setHoverFontSize setHoverFontSize
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    * @see #setHoverWidget setHoverWidget
    * @see #setHoverXShift setHoverXShift
    * @see #setHoverYShift setHoverYShift
    * @see #DEFAULT_HOVER_LOCATION DEFAULT_HOVER_LOCATION
    *
    """
    def setHoverLocation(self, hoverLocation):
        self.getHoverAnnotation().setLocation(hoverLocation)
    
    
    """*
    *
    * Sets the symbol type that GChart will use when positioning
    * hover annotations. GChart positions each hover annotation
    * as if it were associated with a point with the
    * same x,y as the hovered over point, and mapped to the same
    * y-axis, but that appears on a curve with the symbol type
    * specified by this method.
    *
    * <p> If <tt>None</tt> is used (this is the default) GChart
    * will use the symbol type associated with the curve
    * containing the hovered over point.  Since normally you
    * will want hover annotations to be positioned as if they were
    * annotations of the hovered over points, this default is
    * usually appropriate.  <p>
    *
    * However, sometimes you would like the hover annotations to be
    * positioned differently. For example, you might prefer the
    * hover annotations to always appear within a status bar at the
    * bottom of the chart. To achieve this, you could set this
    * property to <tt>ANCHOR_SOUTHWEST</tt>.  Or suppose you
    * always wanted a pie chart's hover annotations to appear in
    * the center of the pie instead of along the outer
    * perimeter. Then you could use <tt>BOX_CENTER</tt>. Or, if you
    * wanted the hover annotations to be positioned relative to the
    * position that the mouse was at when the symbol was first
    * "touched", you could use <tt>ANCHOR_MOUSE</tt>.
    * <p>
    *
    * <i>Tip:</i> Pre v2.4 versions of GChart supported a much
    * simpler, "at-the-mouse", <tt>setTitle</tt>-based, hover
    * feedback that you can emulate using code such as: <p>
    *
    * <pre>
    *     Symbol sym = getCurve().getSymbol()
    *     sym.setHoverAnnotationSymbolType(SymbolType.ANCHOR_MOUSE)
    *     sym.setHoverLocation(AnnotationLocation.SOUTHEAST)
    *     sym.setHoverYShift(-20); # push 20px below mouse
    *                              # (kind of like setTitle does it).
    *
    *     # Convenience/transition-helper method
    *     # formatAsHovertext wraps plain text in appropriate
    *     # HTML so it looks kind of like setTitle-based hovertext.
    *
    *     sym.setHovertextTemplate(
    *       GChart.formatAsHovertext("x=${x}, y=${y}"))
    * </pre>
    * <p>
    *
    * @param hoverAnnotationSymbolType the symbol type that in part
    * determines how the hover annotations get positioned, or
    * <tt>None</tt> (the default) to use the symbol type of the
    * hovered over point.
    *
    * @see #getHoverAnnotationSymbolType getHoverAnnotationSymbolType
    * @see #setHoverLocation setHoverLocation
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverXShift setHoverXShift
    * @see #setHoverYShift setHoverYShift
    * @see GChart#formatAsHovertext GChart.formatAsHovertext
    """
    def setHoverAnnotationSymbolType(self, hoverAnnotationSymbolType):
        self.hoverAnnotationSymbolType = hoverAnnotationSymbolType
    
    """*
    * Specifies the background color used to indicate that the mouse is
    * "touching" (hovering over) a point.
    * <p>
    *
    * Whenever the user "touches" a point on this curve with
    * the curve's mouse-centered "brush", GChart displays the hover
    * feedback for that point, and indicates that the point is
    * the one the hover feedback refers to changing its
    * background color to this color.
    * <p>
    *
    * The default hover selection background color is
    * "transparent". This allows the original symbol to appear
    * within selection rectangles that can be defined via the
    * <tt>setHoverSelectionBorderWidth</tt> and
    * <tt>setHoverSelectionBorderColor</tt> methods (1px thick
    * external gray selection rectangles are used by default).
    * <p>
    *
    * <i>Tip:</i> Because the background selection color
    * will often cover the original symbol, it's usually
    * best to choose a selection background color closely
    * related to the original symbol's background color.
    * For example, if the original symbol were blue, you
    * might use a lighter shade of blue.
    *
    * @param hoverSelectionBackgroundColor a CSS color
    * specification string that specifies the background color used to
    * indicate "hover-selection".
    *
    * @see #getHoverSelectionBackgroundColor
    * getHoverSelectionBackgroundColor
    * @see #setHoverSelectionBorderColor
    * setHoverSelectionBorderColor
    * @see #setHoverSelectionBorderStyle
    * setHoverSelectionBorderStyle
    * @see #setHoverSelectionBorderWidth
    * setHoverSelectionBorderWidth
    * @see #setBrushHeight setBrushHeight
    *
    """
    def setHoverSelectionBackgroundColor(self, hoverSelectionBackgroundColor):
        self.hoverSelectionBackgroundColor = hoverSelectionBackgroundColor
    
    """*
    * Specifies the border color used to indicate that the mouse is
    * "touching" (hovering over) a point.
    * <p>
    *
    * Whenever the user "touches" a point on this curve with
    * the mouse-centered "brush", GChart displays the hover
    * feedback for that point, and indicates that the point is
    * the one the hover feedback refers to by drawing a border
    * around it with the given color.
    * <p>
    *
    * The width of this border, and if the is drawn outside or
    * just inside the rectangles associated with the symbol,
    * can be specified via
    * <tt>setHoverSelectionBorderWidth</tt>.
    *
    * The default hover selection border color is <tt>gray</tt>.
    *
    * @param hoverSelectionBorderColor a CSS color specification string that specifies
    * the color used to indicate "hover-selection", or the special
    * keyword TRANSPARENT_BORDER_COLOR for a cross-browser consistent
    * transparent border.
    *
    * @see #getHoverSelectionBorderColor
    * getHoverSelectionBorderColor
    * @see #setHoverSelectionBorderStyle
    * setHoverSelectionBorderStyle
    * @see #setHoverSelectionBorderWidth
    * setHoverSelectionBorderWidth
    * @see #setBrushHeight setBrushHeight
    *
    """
    def setHoverSelectionBorderColor(self, hoverSelectionBorderColor):
        self.hoverSelectionBorderColor = hoverSelectionBorderColor
    
    
    """*
    * Specifies the border style used to indicate that the mouse is
    * "touching" (hovering over) a point.
    * <p>
    *
    * Whenever the user "touches" a point on this curve with
    * the mouse-centered "brush", GChart displays the hover
    * feedback for that point, and indicates that the point is
    * the one the hover feedback refers to by drawing a border
    * around it with the given style.
    * <p>
    *
    * The width of this border, and if the is drawn outside or
    * just inside the rectangles associated with the symbol,
    * can be specified via
    * <tt>setHoverSelectionBorderWidth</tt>.
    *
    * The default hover selection border style is <tt>solid</tt>.
    *
    * @param hoverSelectionBorderStyle a CSS border style
    * specification string that indicates the style of border used to
    * indicate "hover-selection".
    *
    * @see #getHoverSelectionBorderStyle
    * getHoverSelectionBorderStyle
    * @see #setHoverSelectionBorderWidth
    * setHoverSelectionBorderWidth
    * @see #setHoverSelectionBorderColor
    * setHoverSelectionBorderColor
    * @see #setBrushHeight setBrushHeight
    *
    """
    def setHoverSelectionBorderStyle(self, hoverSelectionBorderStyle):
        self.hoverSelectionBorderStyle = hoverSelectionBorderStyle
    
    
    
    """*
    * Sets the width of the border around the perimeter of
    * rectangles used to indicate that the mouse is
    * "touching" (hovering over) a point.
    * <p>
    *
    * If positive, the border is drawn inside each rendered
    * rectangle of the selected symbol. If negative, the border
    * is drawn outside of those rectangles.
    * <p>
    *
    * <i>Tip:</i> To create the illusion that symbols
    * increase in size when they are "touched", use a hover
    * selection border color that matches the symbol's color
    * along with a negative hover selection border width.  <p>
    *
    * @param borderWidth the width of the border drawn around
    * the perimeter of the selected symbol's rectangles to
    * indicate that the symbol is being "touched: by the mouse.  A
    * negative value adds that border around the outside of the
    * existing rectangles, in effect increasing the selected
    * symbol's size (in pixels).
    *
    * @see #getHoverSelectionBorderWidth
    * getHoverSelectionBorderWidth
    * @see #setHoverSelectionBorderColor setHoverSelectionBorderColor
    * @see #setHoverSelectionBackgroundColor setHoverSelectionBackgroundColor
    * @see #setHoverSelectionBorderStyle
    * setHoverSelectionBorderStyle
    *
    *
    """
    def setHoverSelectionBorderWidth(self, borderWidth):
        self.hoverSelectionBorderWidth = borderWidth
    
    
    
    
    
    """*
    * Specifies if hover selection feedback will be provided
    * for this curve.
    * <p>
    *
    * When enabled, whenever the user "touches" a point on this
    * curve with the mouse-centered "brush", GChart indicates
    * the hover-selected point by adding a selection border
    * around the point, etc.
    * <p>
    *
    * By default, hover selection feedback is enabled.
    * <p>
    *
    * Note that the pop-up hover annotation itself is
    * controlled separately, via the
    * <tt>setHoverAnnotationEnabled</tt> method.
    * <p>
    *
    * @param hoverSelectionEnabled a if True, hover selection feedback is enabled,
    *   if False, hovering over a point does not change its
    *   color.
    *
    * @see #getHoverSelectionEnabled getHoverSelectionEnabled
    * @see #setHoverAnnotationEnabled setHoverAnnotationEnabled
    * @see #setHoverSelectionBackgroundColor setHoverSelectionBackgroundColor
    * @see #setHoverSelectionBorderColor setHoverSelectionBorderColor
    * @see #setHoverSelectionBorderStyle
    * setHoverSelectionBorderStyle
    * @see #setHoverSelectionBorderWidth setHoverSelectionBorderWidth
    * @see #setHoverSelectionSymbolType setHoverSelectionSymbolType
    *
    """
    def setHoverSelectionEnabled(self, hoverSelectionEnabled):
        self.hoverSelectionEnabled = hoverSelectionEnabled
    
    
    """*
    * Specifies the fill spacing that will be used when
    * rendering this curve's hover selection feedback.
    * <p>
    *
    * For more on fill spacing, see
    * <tt>setFillSpacing</tt>.
    * <p>
    *
    * @param selectionFillSpacing fill spacing, in pixels, used
    * when rendering this curve's hover selection feedback or
    * <tt>Double.NaN</tt> (the default) to adopt the curve's
    * fill spacing.
    *
    * @see #getHoverSelectionFillSpacing getHoverSelectionFillSpacing
    * @see #setFillSpacing setFillSpacing
    *
    """
    
    def setHoverSelectionFillSpacing(self, selectionFillSpacing):
        self.hoverSelectionFillSpacing = selectionFillSpacing
    
    """*
    * Specifies the fill thickness that will be used when
    * rendering this curve's hover selection feedback.
    * <p>
    *
    * For more on fill thickness, see
    * <tt>setFillThickness</tt>.
    * <p>
    *
    * @param selectionFillThickness fill thickness, in pixels, used
    * when rendering this curve's hover selection feedback or
    * <tt>GChartConsts.NAI</tt> (the default) to adopt the curve's
    * fill thickness.
    *
    * @see #getHoverSelectionFillThickness getHoverSelectionFillThickness
    * @see #setFillThickness setFillThickness
    *
    """
    def setHoverSelectionFillThickness(self, selectionFillThickness):
        self.hoverSelectionFillThickness = selectionFillThickness
    
    
    
    """*
    * Sets the height of the symbol used to indicate
    * when a given point is being "hovered over" with the
    * mouse.
    * <p>
    *
    * With the default setting of <tt>GChartConsts.NAI</tt>, GChart
    * simply gives the hover selection symbol the same height as
    * the symbol representing the point itself.  Though this
    * default is usually appropriate, you might want the
    * selection symbol to have a larger size so as to increase
    * the visibility of the selected point, etc.
    * <p>
    *
    * @param selectionHeight the height of the symbol used
    * to indicate that that a point has been selected, in
    * pixels, or <tt>GChartConsts.NAI</tt> (the default) to use
    * the height of the symbol representing the selected
    * point.
    *
    *
    * @see #getHoverSelectionHeight getHoverSelectionHeight
    * @see #setHoverSelectionWidth setHoverSelectionWidth
    * @see #setHoverSelectionBorderColor setHoverSelectionBorderColor
    * @see #setHoverSelectionBackgroundColor setHoverSelectionBackgroundColor
    *
    *
    """
    def setHoverSelectionHeight(self, selectionHeight):
        self.hoverSelectionHeight = selectionHeight
    
    
    """*
    * Specifies the URL that will define the image
    * used to render selection feedback for points on
    * the curve associated with this symbol.
    *
    * <p>
    *
    * Specify <tt>None</tt> to use the URL returned by
    * <tt>getBlankImageURL</tt> (this is the default, and gives you a
    * blank 1x1 pixel GIF). Since the image is transparent, the
    * <tt>setHoverSelectionBackgroundColor</tt> method can be used to
    * define the background color of the selection feedback.  <p>
    *
    * Though most applications will do just fine with this default,
    * you can use this method for special selection effects, such
    * creating a semi-transparent "screen" (say, by using an image
    * with alternating transparent and gray pixels) that overlays the
    * selected points.
    * <p>
    *
    * The image is applied in the same way as the symbol's own image
    * URL, but to the internal, system, curve GChart uses to render
    * the selection feedback. See <tt>setImageURL</tt> for additional
    * information.
    *
    * @see #getHoverSelectionImageURL getHoverSelectionImageURL
    * @see #setImageURL setImageURL
    * @see #setBlankImageURL setBlankImageURL
    
    * @param imageURL the url that defines the image used to generate
    * selection feedback for points rendered with this symbol, or
    * <tt>None</tt> to to use GChart's default selection image URL (a
    * 1x1 transparent blank GIF).
    *
    """
    def setHoverSelectionImageURL(self, imageURL):
        self.hoverSelectionImageURL = imageURL
    
    
    """*
    *
    * Sets the symbol type that GChart will use when
    * generating selection feedback. GChart indicates that
    * a point is selected by re-rendering the point <i>as
    * if</i> it had this symbol type (this re-rendering
    * overlays, but need not completely cover, the
    * original rendering).
    *
    * <p> If <tt>None</tt> is used (this is the default) GChart
    * will use the symbol type associated with the original
    * point. This default, which overlays the selection feedback
    * on top of the rendered symbol, is usually appropriate.
    * <p>
    *
    * However, sometimes you would like the selection feedback
    * to use a different symbol type. For example, you might
    * prefer to indicate that a point is selected by drawing a
    * vertical gridline through the point. To achieve this, you
    * could use the <tt>XGRIDLINE</tt> symbol type. Or, you
    * might wish to indicate selection by dropping a vertical
    * line from the center of the selected point to the x-axis.
    * In this case, you could use <tt>VBAR_SOUTH</tt> as the
    * hover selection symbol type.
    * <p>
    *
    * <i>Note:</i> The special mouse related symbol types (those with
    * names matching <tt>ANCHOR_MOUSE*</tt>) are intended for use
    * in positioning hover popup annotations (via
    * <tt>setHoverAnnotationSymbolType</tt>). They are not expected to be
    * useful, and could potentially cause confusion, if used as the
    * symbol type passed to this method.
    *
    * <p>
    *
    * @param hoverSelectionSymbolType the symbol type that in
    * part determines how selection feedback for a hovered over
    * point is drawn, or <tt>None</tt> (the default) to use the
    * symbol type of the hovered over point.
    *
    * @see #getHoverSelectionSymbolType getHoverSelectionSymbolType
    * @see Symbol#setHoverSelectionBackgroundColor
    * setHoverSelectionBackgroundColor
    * @see Symbol#setHoverSelectionBorderColor setHoverSelectionBorderColor
    * @see Symbol#setHoverSelectionBorderWidth setHoverSelectionBorderWidth
    * @see Symbol#setHoverSelectionHeight setHoverSelectionHeight
    * @see Symbol#setHoverSelectionWidth setHoverSelectionWidth
    * @see Symbol#setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    *
    """
    def setHoverSelectionSymbolType(self, hoverSelectionSymbolType):
        #       throwExceptionOnAnchorMouse(hoverSelectionSymbolType)
        self.hoverSelectionSymbolType = hoverSelectionSymbolType
    
    """*
    * Sets the width of the symbol used to indicate
    * when a given point is being "hovered over" with the
    * mouse.
    * <p>
    *
    * With the default setting of <tt>GChartConsts.NAI</tt>, GChart
    * simply gives the hover selection symbol the same width as
    * the symbol representing the point itself.  Though this
    * default is usually appropriate, you might want the
    * selection symbol to have a larger size so as to increase
    * the visibility of the selected point, etc.
    * <p>
    *
    * @param selectionWidth the width of the symbol used to
    * indicate that that a point has been selected, in
    * pixels, or
    * <tt>GChartConsts.NAI</tt> (the default) to use the width of the
    * symbol representing the selected point.
    *
    *
    * @see #getHoverSelectionWidth getHoverSelectionWidth
    * @see #setHoverSelectionHeight setHoverSelectionHeight
    * @see #setHoverSelectionBorderColor setHoverSelectionBorderColor
    * @see #setHoverSelectionBackgroundColor setHoverSelectionBackgroundColor
    *
    *
    """
    def setHoverSelectionWidth(self, selectionWidth):
        self.hoverSelectionWidth = selectionWidth
    
    
    
    
    """*
    ** Defines the "hover-text" that appears whenever the user
    ** points their mouse at a point on the curve.
    ** @param hovertextTemplate defines the hoverText to display when the mouse
    **   moves over a point on this curve, with <tt>${x}</tt>,
    **   <tt>${y}</tt> and
    **   <tt>${pieSliceSize}</tt> parameters replaced as described above, and
    **   custom parameters replaced as defined by the parent
    **   GChart's <tt>HoverParameterInterpreter</tt>.
    **
    ** @see #getHovertextTemplate getHovertextTemplate
    ** @see Curve.Point#getHovertext getHovertext
    ** @see HoverParameterInterpreter HoverParameterInterpreter
    ** @see GChart#setHoverParameterInterpreter setHoverParameterInterpreter
    ** @see HoverUpdateable HoverUpdateable
    ** @see GChart.Curve.Point#setAnnotationText setAnnotationText
    ** @see #DEFAULT_HOVERTEXT_TEMPLATE DEFAULT_HOVERTEXT_TEMPLATE
    ** @see #DEFAULT_PIE_SLICE_HOVERTEXT_TEMPLATE
    **   DEFAULT_PIE_SLICE_HOVERTEXT_TEMPLATE
    *"""
    def setHovertextTemplate(self, hovertextTemplate):
        if self.hovertextTemplate != hovertextTemplate:
            self.hovertextChunks = None; # invalidates prev chunk-parse
        
        self.hovertextTemplate = hovertextTemplate
    
    
    """*
    * Specifies a <tt>HoverUpdateable</tt> widget that will be
    * used to display the hover annotations associated with this
    * symbol. If <tt>None</tt>, GChart's built-in,
    * <tt>setHovertextTemplate</tt>-based, text or HTML
    * based hover annotations will instead be used.  <p>
    *
    * Whenever the rectangular "brush" centered on the current
    * mouse position "touches" a point on this symbol's parent
    * curve, GChart will first call the <tt>hoverUpdate</tt>
    * method of this "hover-widget", and then position it
    * appropriately relative to the touched point. Most
    * applications will want to implement <tt>hoverUpdate</tt> so as to
    * populate the hover widget with detailed information about
    * the touched point. For example, to emulate GChart's
    * default hover feedback, you could extend an <tt>HTML</tt>
    * widget and, within the <tt>hoverUpdate</tt> method, use
    * the <tt>setHTML</tt> method to set the widget's HTML to
    * the expanded hover text returned by
    * <tt>hoveredOverPoint.getHovertext()</tt>.  <p>
    *
    * The exact position of the hover widget relative to the
    * touched point is defined by the companion methods,
    * <tt>setHoverLocation</tt>,
    * <tt>setHoverAnnotationSymbolType</tt>,
    * <tt>setHoverXShift</tt>, and <tt>setHoverYShift</tt>.
    *
    *
    * @param hoverWidget a <tt>Widget</tt> that
    * implements the <tt>HoverUpdateable</tt> interface that GChart will
    * use when generating this symbol's widget-based hover annotations, or
    * <tt>None</tt> to use GChart's text or HTML based hover
    * annotations (the other two parameters can still be used
    * to specify upper-bounds on the width and height of this
    * default hover text).
    *
    *  @param widthUpperBound an upper bound on the width of
    *  the widget (or default hover annotation) in pixels.
    *  Use GChartConsts.NAI to get the GChart-determined default.
    *
    *  @param heightUpperBound an upper bound on the height of the
    *  widget (or default hover annotation) in pixels. Use GChartConsts.NAI
    *  to get the GChart-determined default.
    *
    * @see #getHoverWidget getHoverWidget
    * @see Curve.Point#getHovertext getHovertext
    * @see HoverUpdateable HoverUpdateable
    * @see #setHoverFontWeight setHoverFontWeight
    * @see #setHoverFontColor setHoverFontColor
    * @see #setHoverFontStyle setHoverFontStyle
    * @see #setHoverFontSize setHoverFontSize
    * @see #setHoverLocation setHoverLocation
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverXShift setHoverXShift
    * @see #setHoverYShift setHoverYShift
    *
    """
    
    
    def setHoverWidget(self, hoverWidget,
                widthUpperBound=GChartConsts.DEFAULT_WIDGET_WIDTH_UPPERBOUND,
                heightUpperBound=GChartConsts.DEFAULT_WIDGET_HEIGHT_UPPERBOUND):
        if None != hoverWidget  and  not isinstance(hoverWidget, Widget):
            raise IllegalArgumentException(
            "hoverWidget must either be None or a Widget.")
        
        self.getHoverAnnotation().setWidget(hoverWidget,
                                            widthUpperBound, heightUpperBound)
        
    
    """*
    * Specifies the number of pixels (along the x-axis) to
    * move this symbol's hover annotations from their default,
    * <tt>AnnotationLocation</tt>-defined, point-relative
    * locations.
    * <p>
    *
    * Actual positional shifts are defined via the same
    * conventions as are used by <tt>setAnnotationXShift</tt>.
    * See that method for further details.
    *
    * @see #getHoverXShift getHoverXShift
    * @see GChart.Curve.Point#setAnnotationXShift setAnnotationXShift
    * @see #setHoverFontWeight setHoverFontWeight
    * @see #setHoverFontColor setHoverFontColor
    * @see #setHoverFontStyle setHoverFontStyle
    * @see #setHoverFontSize setHoverFontSize
    * @see #setHoverLocation setHoverLocation
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverWidget setHoverWidget
    * @see #setHoverYShift setHoverYShift
    *
    """
    def setHoverXShift(self, xShift):
        self.getHoverAnnotation().setXShift(xShift)
    
    
    """*
    * Specifies the number of pixels (along the y-axis) to
    * move this symbol's hover annotations from their default,
    * <tt>AnnotationLocation</tt>-defined, point-relative
    * locations.
    * <p>
    *
    * Actual positional shifts are defined via the same
    * conventions as are used by <tt>setAnnotationYShift</tt>.
    * See that method for further details.
    *
    * @see #getHoverYShift getHoverYShift
    * @see GChart.Curve.Point#setAnnotationYShift setAnnotationYShift
    * @see #setHoverFontWeight setHoverFontWeight
    * @see #setHoverFontColor setHoverFontColor
    * @see #setHoverFontStyle setHoverFontStyle
    * @see #setHoverFontSize setHoverFontSize
    * @see #setHoverLocation setHoverLocation
    * @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    * @see #setHovertextTemplate setHovertextTemplate
    * @see #setHoverWidget setHoverWidget
    * @see #setHoverXShift setHoverXShift
    *
    """
    def setHoverYShift(self, yShift):
        self.getHoverAnnotation().setYShift(yShift)
    
    
    
    """*
    * Specifies the URL that will define the image
    * used to represent the points on this curve.
    *
    * @see #getImageURL getImageURL
    * @see #setBlankImageURL setBlankImageURL
    * @see GChart#setPlotAreaImageURL setPlotAreaImageURL
    * @see Curve.Point#setAnnotationWidget setAnnotationWidget
    * @see Curve.Point#setAnnotationText setAnnotationText
    * @see Curve.Point#setAnnotationLocation setAnnotationLocation
    * @see Symbol#setSymbolType setSymbolType
    * @see SymbolType#NONE SymbolType.NONE
    *
    * @param imageURL the url that defines the
    * image within all the rectangular elements used to draw
    * this symbol on the chart, or
    * <tt>None</tt> to revert to GChart's default (a 1x1 transparent
    * blank GIF).
    *
    """
    def setImageURL(self, imageURL):
        self.imageURL = imageURL
    
    
    """*
    ** Sets the height of this symbol (including any specified border)
    ** in pixels.
    ** <p>
    **
    ** Symbols for drawing vertical bars and symbols defining
    ** vertical lines between points or across the entire chart,
    ** compute their heights automatically based on curve data,
    ** axes limits, specified baselines, etc. These symbols, namely
    ** <tt>XGRIDLINE</tt> and all those whose names begin with
    ** <tt>VBAR_</tt> will ignore this height setting.
    **
    ** <p>
    ** @param height height of this symbol, in pixels.
    **
    ** @see #getHeight getHeight
    *"""
    def setHeight(self, height):
        self.getParent().invalidate()
        self.height = height
        self.modelHeight = Double.NaN
    
    """*
    ** Sets the height of this symbol (including any specified border)
    ** in model units (arbitrary, user-defined, units). Model
    ** units are the same units in which the points on the
    ** chart are specified and charted.
    ** <p>
    **
    ** Specification of the modelHeight undefines (that is, sets
    ** to <tt>GChartConsts.NAI</tt>) any previous pixel-based
    ** specification made via <tt>setHeight</tt>.
    **
    ** <p> Symbols for drawing vertical bars and symbols defining
    ** vertical lines between points or across the entire chart,
    ** compute their heights automatically based on curve data,
    ** axes limits, specified baselines, etc. These symbols, namely
    ** <tt>XGRIDLINE</tt> and all those whose names begin with
    ** <tt>VBAR_</tt> will ignore this height setting.
    **
    ** <p>
    ** @param modelHeight height of this symbol, in model units
    **
    ** @see #getModelHeight getModelHeight
    ** @see #setHeight setHeight
    ** @see #setModelWidth setModelWidth
    ** @see #setWidth setWidth
    *"""
    def setModelHeight(self, modelHeight):
        self.getParent().invalidate()
        self.modelHeight = modelHeight
    
    """*
    ** Sets the width of this symbol (including any specified border)
    ** in model units. Model units are an arbitrary, user-defined
    ** units system associated with the x,y coordinates of
    ** points displayed on the chart.
    **
    ** <p> Specification of a symbol's model width undefines (that
    ** is, sets to <tt>GChartConsts.NAI</tt>) any previous, pixel-based,
    ** width specification made via <tt>setWidth</tt>.  <p>
    **
    ** Symbols for drawing horizontal bars, and symbols defining
    ** horizontal lines between points or across the entire chart,
    ** compute their widths automatically based on curve data,
    ** axes limits, specified baseline, etc. These symbols,
    ** namely <tt>YGRIDLINE</tt> and all those whose
    ** names begin with <tt>HBAR_</tt> will ignore this width
    ** setting.
    **
    ** <p>
    ** @param modelWidth width of this symbol, in model units.
    **
    ** @see #setModelHeight setModelHeight
    ** @see #setWidth setWidth
    ** @see #setHeight setHeight
    **
    *"""
    def setModelWidth(self, modelWidth):
        self.getParent().invalidate()
        self.modelWidth = modelWidth
    
    
    """*
    ** Specifies a value that defines the angular orientation of
    ** the first edge of the pie slice associated with this
    ** symbol.  (An additional clockwise rotation as defined by
    ** <tt>setPieSliceSize</tt> defines the angular orientation
    ** of the second edge of the pie slice).
    **
    ** <p> When specified explicitly, the value must be a
    ** fraction >= 0 and < 1, with 0 representing due south,
    ** 0.25 an additional clockwise angular rotation (starting
    ** at due south) that is 25% of the full, 360 degree
    ** rotation (and thus, if you can follow these gyrations, is
    ** due west), 0.5 representing a 50% clockwise angular
    ** rotation from due south (thus, due north), .75 a 75%
    ** clockwise rotation (and thus, due east), etc.
    **
    ** <p> If the specially recognized value,
    ** <tt>Double.NaN</tt>, is specified, orientation is
    ** chosen so as to make this slice appear adjacent to
    ** the previous slice, (assuming it has the same x,y
    ** as the previous slice and is thus part of the same
    ** pie figure). If this symbol/point represents the
    ** very first pie slice, <tt>Double.NaN</tt>
    ** causes the slice to be oriented as specified via
    ** the <tt>setInitialPieSliceOrientation</tt> method
    ** (by default, that's due south).
    **
    ** Note that though this value can be set regardless of the
    ** symbol's <tt>SymbolType</tt>, it only has an impact on
    ** how the symbol is rendered if the symbol has one of the
    ** pie slice symbol types (e.g.
    ** <tt>PIE_SLICE_VERTICAL_SHADING</tt>).
    **
    ** @param pieSliceOrientation angle at which first edge of pie
    ** slice appears, expressed as a fraction of a full
    ** 360 degree (2*Pi radians) clockwise rotation from an initial due
    ** south position (the 6 o'clock position) required to reach the first
    ** edge of the pie slice.
    **
    **
    **
    ** @see #getPieSliceOrientation getPieSliceOrientation
    ** @see #setPieSliceSize setPieSliceSize
    ** @see GChart#setInitialPieSliceOrientation setInitialPieSliceOrientation
    **
    """
    def setPieSliceOrientation(self, pieSliceOrientation):
        idx = self.getChart().getCurveIndex(self.getParent())
        self.getChart().invalidateDependentSlices(idx)
        if self.pieSliceOrientation!=Double.NaN  and  (self.pieSliceOrientation < 0  or  self.pieSliceOrientation >=1):
            raise IllegalArgumentException(
            "pieSliceOrientation="+str(self.pieSliceOrientation)+"; "+
            "pieSliceOrientation must be >=0 and < 1, or else " +
            "equal to Double.NaN.")
        
        self.pieSliceOrientation = pieSliceOrientation
    
    
    """*
    ** Specifies a value that defines the angular size of
    ** any pie slice associated with this symbol.
    **
    ** <p> This must be value between 0 and 1.  0.25 represents
    ** a quarter pie slice, 0.5 a half pie, 1 a full pie, etc.
    **
    ** <p><i>Note:</i> To create a complete pie, you must arrange
    ** things so that the sum of all of your pie slice sizes adds up to
    ** exactly 1.0. If they sum to more than 1, some slices will cover
    ** up others; it they sum to less, your pie will have missing
    ** slices. You can assure you get a full pie, regardless of the
    ** original slice sizes by normalizing your slice sizes.
    ** Specifically, divide each original slice size by the sum over
    ** all of the original slice sizes.  For example, if the original
    ** slice sizes were 1, 2, and 2 you could divide them by their sum
    ** (1 + 2 + 2 = 5) to obtain normalized slice sizes of 0.2, 0.4,
    ** and 0.4.  <p>
    **
    ** Note that though this value can be set regardless of the
    ** symbol's current <tt>SymbolType</tt>, it only has an
    ** impact on how the symbol is rendered if the symbol has
    ** one of the pie slice symbol types (e.g.
    ** <tt>PIE_SLICE_VERTICAL_SHADING</tt>).
    **
    ** @param pieSliceSize Fraction of a full pie subtended by
    **  this particular pie slice. Must be between 0 and 1,
    **  inclusive.
    **
    ** @see #getPieSliceSize getPieSliceSize
    ** @see #setPieSliceOrientation setPieSliceOrientation
    **
    """
    def setPieSliceSize(self, pieSliceSize):
        idx = self.getChart().getCurveIndex(self.getParent())
        self.getChart().invalidateDependentSlices(idx)
        if not GChartUtil.withinRange(pieSliceSize,0,1):
            raise IllegalArgumentException(
            "pieSliceSize="+self.pieSliceSize+"; the requirement: "+
            "0.0 <= pieSliceSize <= 1.0 must be satisfied.")
        
        self.pieSliceSize = pieSliceSize
    
    
    """*
    ** Sets the type of this symbol.
    ** <p>
    **
    ** <i>Note:</i> The special mouse related symbol types (those with
    ** names that begin with <tt>ANCHOR_MOUSE</tt>) are intended for use
    ** in positioning hover popup annotations (via
    ** <tt>setHoverAnnotationSymbolType</tt>). They are not expected to be
    ** useful, and could potentially cause confusion, if used as the
    ** symbol types of ordinary curves.
    **
    ** @param symbolType the symbol type for this symbol.
    ** @see SymbolType SymbolType
    ** @see SymbolType#ANCHOR_MOUSE ANCHOR_MOUSE
    ** @see #setHoverAnnotationSymbolType setHoverAnnotationSymbolType
    **
    """
    def setSymbolType(self, symbolType):
        #      throwExceptionOnAnchorMouse(symbolType)
        self.getParent().invalidate()
        # will invalidate dependent slices if it was previously a pie slice
        idx = self.getChart().getCurveIndex(self.getParent())
        self.getChart().invalidateDependentSlices(idx)
        self.symbolType = symbolType
        # will invalidate dependent slices if it is now a pie slice
        idx = self.getChart().getCurveIndex(self.getParent())
        self.getChart().invalidateDependentSlices(idx)

    
    
    
    """*
    ** Sets the width of this symbol (including any specified border)
    ** in pixels.
    ** <p>
    **
    ** Symbols for drawing horizontal bars, and symbols defining
    ** horizontal lines between points or across the entire chart,
    ** compute their widths automatically based on curve data,
    ** axes limits, specified baseline, etc. These symbols, namely
    ** <tt>YGRIDLINE</tt> and all those whose names begin with
    ** <tt>HBAR_</tt> will ignore this width setting.
    **
    ** <p>
    ** @param width width of this symbol, in pixels
    **
    ** @see #setHeight setHeight
    **
    *"""
    def setWidth(self, width):
        self.getParent().invalidate()
        self.width = width
        self.modelWidth = Double.NaN
    
    
    
    """
    * Copies properties of the "from" symbol to this symbol.
    *
    * This isn't a generic copy, but is used only when copying
    * the properties of the hovered-over curve into the
    * system curves used to render the selection feedback and
    * hover annotations (it contains some special logic needed
    * only in that context).
    *
    """
    def copy(self, fc):
        self.setBackgroundColor(fc.getBackgroundColor())
        self.setBaseline(fc.getBaseline())
        self.setBorderColor(fc.getBorderColor())
        self.setBorderStyle(fc.getBorderStyle())
        self.setBorderWidth(fc.getBorderWidth())
        self.setFillSpacing(fc.getFillSpacing())
        self.setFillThickness(fc.getFillThickness())
        #       setHoverAnnotationEnabled(fc.getHoverAnnotationEnabled())
        self.setHoverFontColor(fc.getHoverFontColor())
        self.setHoverFontSize(fc.getHoverFontSize())
        self.setHoverFontStyle(fc.getHoverFontStyle())
        self.setHoverFontWeight(fc.getHoverFontWeight())
        self.setHoverLocation(fc.getHoverLocation())
        self.setHoverAnnotationSymbolType(fc.getHoverAnnotationSymbolType())
        self.setHoverSelectionBackgroundColor(fc.getHoverSelectionBackgroundColor())
        self.setHoverSelectionBorderColor(fc.getHoverSelectionBorderColor())
        self.setHoverSelectionBorderStyle(fc.getHoverSelectionBorderStyle())
        self.setHoverSelectionBorderWidth(fc.getHoverSelectionBorderWidth())
        #       setHoverSelectionEnabled(fc.getHoverSelectionEnabled())
        self.setHovertextTemplate(fc.getHovertextTemplate())
        self.setHoverWidget(fc.getHoverWidget())
        self.setHoverXShift(fc.getHoverXShift())
        self.setHoverYShift(fc.getHoverYShift())
        self.setImageURL(fc.getImageURL())
        # Model and pixel variants of width/height actually
        # represent a single underlying property (setting one,
        # unsets the other, etc.). Logic below reflects this.
        if not Double.NaN==(fc.getModelHeight()):
            self.setModelHeight(fc.getModelHeight())
        
        else:
            self.setHeight(fc.getHeight())
        
        if not Double.NaN==(fc.getModelWidth()):
            self.setModelWidth(fc.getModelWidth())
        
        else:
            self.setWidth(fc.getWidth())
        
        
        self.setPieSliceOrientation(fc.getPieSliceOrientation())
        self.setDefaultPieSliceOrientation(fc.getDefaultPieSliceOrientation())
        self.setPieSliceSize(fc.getPieSliceSize())
        self.setSymbolType(fc.getSymbolType())
        
    
    def getAnnotation(self):
        if self.annotation is None:
            self.annotation = Annotation()
        
        return self.annotation
    
    
    """*
    ** Returns this symbol's height, as previously set by
    ** <tt>setHeight</tt>.
    **
    ** @return the previously set symbol height, in pixels.
    **
    ** @see #setHeight setHeight
    """
    
    # Pixel height of symbol when rendered on given plot panel
    def getHeight(self, pp=None, onY2=None):
        
        if pp is None and onY2 is None:
            return self.height

        mH = self.getModelHeight()
        if (Double.NaN==(mH)):
            result = self.getHeight()
        
        else:
            result = pp.dyToPixel(mH,onY2)
        
        
        return result
    
    """*
    ** Returns this symbol's width
    ** as previously set by <tt>setWidth</tt>.
    ** <p>
    **
    ** <i>Warning:</i> This method won't return the correct
    ** pixel width associated with a <tt>setModelWidth</tt>
    ** setting, as you might have expected.  It only returns
    ** the pixel width you last explicitly specified via
    ** <tt>setWidth</tt>.
    **
    ** <p>
    **
    ** @return the previously set symbol width, in pixels
    **
    ** @see #setWidth setWidth
    ** @see #setModelWidth setModelWidth
    """
    
    
    # Pixel width of symbol when rendered on given plot panel
    def getWidth(self, pp=None):
        
        if pp is None:
            return self.width

        mW = self.getModelWidth()
        if (Double.NaN==(mW)):
            result = self.getWidth()
        
        else:
            result = pp.dxToPixel(mW)
        
        
        return result
    
    
    
    """ Renders the symbol at the specified position within the
    plot panel, by creating appropriately positioned Image
    and Grid (for any Annotation associated with this symbol
    rendering) objects within the panel.  So-rendered symbols
    are used to represent: each point on a curve with any
    associated point annotations, axes, gridlines, ticks and
    their tick-labels. """
    
    def realizeSymbol(self, pp, grp, arp, annotation,
                            onY2, clipPlotArea, clipDecoratedChart,
                            drawMainSymbol, x, y, prevX, prevY,
                            nextX, nextY):
        self.getSymbolType().realizeSymbol(pp, grp, arp, self, annotation,
                                            onY2,
                                            clipPlotArea,
                                            clipDecoratedChart,
                                            drawMainSymbol,
                                            x, y,
                                            prevX, prevY, nextX, nextY)
                                            
                                        
    
    
    
    
    
 # end of class Symbol


