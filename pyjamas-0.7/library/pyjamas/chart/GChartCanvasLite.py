"""
* Copyright 2007,2008,2009 John C. Gunther
* Most of this GChartCanvasLite interface was extracted from GWTCanvas,
* a part of the GWT incubator project
* which is Copyright Google, Inc.
* and also licenced under Apache 2.0.
*
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
"""

"""*
* Defines the features of a canvas (vector graphics) widget
* that (once you teach GChart how to create such widgets via
* the <tt>setCanvasFactory</tt> method) GChart can exploit to
* render your charts more quickly and with higher resolution.
*
* <p>
*
* Names, method signatures, and javadoc comments for this
* interface are mostly copied from, and a proper subset of,
* the GWT incubator's <a
* href="http:#code.google.com/p/google-web-toolkit-incubator/wiki/GWTCanvas">
* GWTCanvas widget</a>. Specifically, for simplicity, features
* of <tt>GWTCanvas</tt> that GChart can't exploit, such as gradients and
* transformations, have been omitted, and only ordinary CSS
* and RGBA color strings (not the special <tt>GWTCanvas
* Color</tt> type) are supported.
* <p>
*
* The original <tt>GWTCanvas</tt> code is copyright Google, Inc.  under
* the terms of the Apache 2.0 license.<p>
*
*
* <i>Tip:</i> To easily bolt-on <tt>GWTCanvas</tt> to render your
* charts more quickly and with higher resolution, just add the
* <tt>gwt-incubator.jar</tt> to your build path, and copy the
* boilerplate code in the <tt>setCanvasFactory</tt> method's
* javadocs into the module that contains your application's
* EntryPoint class. If you decide instead to use a different GWT
* cross-browser vector graphics widget, you can still use that
* boilerplate as a starting point for your own, custom, interfacing
* code.
* <p>
*
* <small> GChart requires that the background color of the
* canvas element as a whole be transparent (no background
* color).  This is needed because, to facilitate single-curve
* updating, GChart stitches together the canvas based
* rendering of a chart from a series of smaller, overlaid,
* canvas widgets.  Since transparent backgrounds are the
* default for <tt>GWTCanvas</tt>, and likely for other GWT vector
* graphics widgets, you are not expected to have to do
* anything special to meet this requirement.  </small>
*
*
* @see GChartCanvasFactory GChartCanvasFactory
* @see GChart#setCanvasFactory setCanvasFactory
* @see GChart.Symbol#setFillSpacing setFillSpacing
* @see GChart.Symbol#setFillThickness setFillThickness
*
*
*"""
interface GChartCanvasLite {
    """*
    * Draws an arc. If the context has a non-empty path, then the method must add a
    * straight line from the last point in the path to the start point of the arc.
    *
    * @param x center X coordinate
    * @param y center Y coordinate
    * @param radius radius of drawn arc
    * @param startAngle angle measured from positive X axis to start of arc CW
    * @param endAngle angle measured from positive X axis to end of arc CW
    * @param antiClockwise direction that the arc line is drawn
    """
    void arc(double x, double y, double radius, double startAngle, double endAngle, boolean antiClockwise)
    """*
    * Erases the current path and prepares it for a path.
    """
    void beginPath()
    """*
    * Clears the entire canvas.
    """
    void clear()
    """*
    * Closes the current path. "Closing" simply means that a line is drawn
    * from the last element in the path back to the first.
    """
    void closePath()
    """*
    * Fills the current path according to the current fillstyle.
    """
    void fill()
    """*
    * Adds a line from the last point in the current path to the
    * point defined by x and y.
    *
    * @param x x coord of point
    * @param y y coord of point
    """
    void lineTo(double x, double y)
    """*
    * Makes the last point in the current path be <b>(x,y)</b>.
    *
    * @param x x coord of point
    * @param y y coord of point
    """
    void moveTo(double x, double y)
    
    """*
    * Resizes the canvas.
    *
    * @param width width of canvas drawing area in pixels
    * @param height height of canvas drawing area in pixels
    *
    """
    void resize(int width, int height)
    """*
    * Set the current Fill Style to the specified color.
    * <p>
    *
    * Whenever GChart uses canvas to fill-in a symbol's interior (e.g.
    * the interior part, excluding the border, of a solid-fill pie
    * slice), it passes the symbol's canvas fill style string (which is
    * specified via <tt>Symbol.setBackgroundColor</tt>) to this method.
    * It then uses the <tt>fill</tt> method of this interface to fill in
    * the symbol's interior with this color.
    *
    * <p>
    *
    * Your method should be able to handle any color specification
    * string likely to be passed into
    * <tt>Symbol.setBackgroundColor</tt>, see that method for full
    * details for the kinds of strings that are supported.
    *
    * @see GChart.Symbol#setBackgroundColor setBackgroundColor
    * @see #fill fill
    *
    * @param canvasFillStyle the fill style specification string. You may
    * assume that GChart will pass you either a standard CSS color
    * specification string, or an RGBA extension of this
    * standard CSS format, such as <tt>rgba(255,255,255,0.5)</tt>.
    *
    """
    void setFillStyle(String canvasFillStyle)
    """*
    * Sets the current context's linewidth. Line width is the thickness
    * of a stroked line.
    * <p>
    *
    * GChart will obtain the width's passed into this method from those
    * specified by the <tt>Symbol.setBorderWidth</tt> method (which
    * defines the widths of stroked borders around any canvas-rendered
    * line, area, or pie-slice chart elements) and from the
    * <tt>Symbol.setFillThickness</tt> method (which defines the
    * thickness of a line chart's connecting lines).
    *
    * <p>
    *
    * @see GChart.Symbol#setBorderWidth setBorderWidth
    * @see GChart.Symbol#setFillThickness setFillThickness
    *
    * @param width the width of the stroked line, in pixels
    """
    void setLineWidth(double width)
    """*
    * Set the current Stroke Style to the specified color.
    *
    * <p>
    *
    * GChart will obtain the color strings passed into this method
    * from those specified by the <tt>Symbol.setBorderColor</tt>
    * method. You can assume that these strings will be either in
    * standard CSS or the extended RGBA format, see
    * <tt>Symbol.setBorderColor</tt> for full details.  These
    * colors will become the colors of the stroked borders around
    * any canvas-rendered line, area, or pie-slice chart elements.
    *
    *
    * <p>
    *
    * @see GChart.Symbol#setBorderColor setBorderColor
    * @see #stroke stroke
    *
    * @param canvasStrokeStyle the stroke style specification string.
    * You may assume that, during rendering, GChart will pass you either
    * a standard CSS color specification string, or an RGBA
    * extension of this standard CSS format such as
    * <tt>rgba(255,255,255,0.5)</tt> for semi-transparent white.
    *
    *
    """
    void setStrokeStyle(String canvasStrokeStyle)
    """*
    * Strokes the current path according to the current stroke style.
    """
    void stroke()



