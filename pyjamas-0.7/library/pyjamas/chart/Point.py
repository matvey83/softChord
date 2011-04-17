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

from pyjamas.chart.GChartConsts import DEFAULT_WIDGET_WIDTH_UPPERBOUND
from pyjamas.chart.GChartConsts import NAI
from pyjamas.chart.GChartConsts import DEFAULT_WIDGET_HEIGHT_UPPERBOUND
from pyjamas.chart.Annotation import Annotation
from pyjamas.chart import HovertextChunk

"""*
** Represents a single point on one of the chart's
** curves. This includes the x, y values of the point in
** "model coordinates" (arbitrary, application-specific,
** units), as well as an optional annotation (text label)
** for the point.
** <p>
** To create points, use a curve's <tt>addPoint</tt> method.
**
** @see Curve#addPoint addPoint
*"""
class Point:

    # Points to index of next point in a vertical or horizontal
    # band (used by the <tt>bandSeparatePoints</tt> method).
    def getINextInBand(self):
        return self.iNextInBand

    def setINextInBand(self, iNext):
        self.iNextInBand = iNext

    def __init__(self, curve, x, y):
        self.curve = curve
        self.x = x
        self.y = y
        self.iNextInBand = NAI
        self.annotation = None


    """*
    ** Returns True if annotation will be rendered in a bold,
    ** or False if in normal, weight font.
    **
    ** @return if this annotation is in bold or not.
    **
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    *"""
    def getAnnotationFontWeight(self):
        return self.getAnnotation().getFontWeight()


    """*
    ** Returns the color of the font used to display the point's
    **   annotation text.
    **
    ** @return CSS color string defining the annotation's color
    **
    ** @see #setAnnotationFontColor setAnnotationFontColor
    *"""
    def getAnnotationFontColor(self):
        return self.getAnnotation().getFontColor()



    """*
    ** Returns the CSS font-style in which the text of this
    **  annotation will be rendered.
    **
    ** @return the font-style used by this annotation (italic,
    **   normal, etc.)
    **
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    *"""
    def getAnnotationFontStyle(self):
        return self.getAnnotation().getFontStyle()


    """*
    ** Returns the CSS font size of this point's annotation
    ** (text label), in pixels.
    **
    ** @return the font size of this point's annotation.
    **
    ** @see #setAnnotationFontSize setAnnotationFontSize
    *"""
    def getAnnotationFontSize(self):
        return self.getAnnotation().getFontSize()




    """* Returns the previously specified location, relative
    ** to the symbol representing the point, of the
    ** annotation (text label) associated with this point.
    **
    ** @return relative location of the point's annotation
    **
    ** @see #setAnnotationLocation setAnnotationLocation
    **
    *"""
    def getAnnotationLocation(self):
        result = self.getAnnotation().getLocation()
        if None == result:
            result = self.getParent().getSymbol().getSymbolType().defaultAnnotationLocation()

        return result

    """*
    ** Returns the text of this point's annotation.
    **
    ** @return the text of the annotation, or <tt>None</tt> if this
    **   point either lacks an annotation or uses a widget-based
    **   annotation.
    **
    ** @see #setAnnotationText setAnnotationText
    **
    *"""
    def getAnnotationText(self):
        return self.getAnnotation().getText()


    """*
    * Returns the widget reference that defines this point's
    * annotation as previously specified by
    * <tt>setAnnotationWidget</tt>. Returns <tt>None</tt> if
    * the annotation has not yet been specified, or if it was
    * defined via <tt>setAnnotationText</tt>.
    *
    * @return reference to the widget defining this point's
    * annotation, or <tt>None</tt> if none.
    *
    * @see #setAnnotationWidget setAnnotationWidget
    * @see #setAnnotationText setAnnotationText
    *
    """

    def getAnnotationWidget(self):
        return self.getAnnotation().getWidget()


    """*
    ** Returns True is the point's annotation is visible, False
    ** otherwise
    **
    ** @return if the a annotation defined for this point will
    **    be visible or not after the next update.
    **
    ** @see #setAnnotationVisible setAnnotationVisible
    *"""
    def getAnnotationVisible(self):
        return self.getAnnotation().getVisible()


    """*
    ** Returns the distance, in pixels, that this annotation
    ** will be shifted along the x-axis from it's default
    ** location.  <p>
    **
    ** @return amount annotation will be shifted along the x-axis,
    **   in pixels.
    **
    ** @see #setAnnotationXShift setAnnotationXShift
    *"""
    def getAnnotationXShift(self):
        return self.getAnnotation().getXShift()


    """*
    ** Returns the distance, in pixels, that this annotation
    ** will be shifted along the y-axis from it's default
    ** location.  <p>
    **
    ** @return amount annotation will be shifted along the y-axis,
    **   in pixels.
    **
    ** @see #setAnnotationYShift setAnnotationYShift
    *"""
    def getAnnotationYShift(self):
        return self.getAnnotation().getYShift()


    """* Returns the <tt>Curve</tt> that this point was added to.
    **
    ** @return a reference to the <tt>Curve</tt> that contains
    ** this point (its "parent").
    **
    *"""
    def getParent(self):
        return self.curve

    """* Returns the x-coordinate of this point in "model units"
    ** (arbitrary, application-specific, units).
    **
    ** @return the x-coordinate, in model units
    **
    ** @see #setX setX
    ** @see #setY setY
    ** @see #getY getY
    **
    *"""
    def getX(self):
        return self.x

    """* Returns the y-coordinate of this point in "model units"
    ** (arbitrary, application-specific, units).
    **
    ** @return the y-coordinate, in model units
    **
    ** @see #getX getX
    ** @see #setX setX
    ** @see #setY setY
    **
    *"""
    def getY(self):
        return self.y


    """*
    ** Specifies the weight of the font that will be used
    ** to render the text of this point's annotation.
    ** <p>
    **
    ** @param cssWeight A standard CSS font-weight
    **    specification such as normal, bold, bolder, lighter,
    **    100, 200, ... 900, or inherit
    **
    ** @see #getAnnotationFontWeight getAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    *"""
    def setAnnotationFontWeight(self, cssWeight):
        self.getParent().invalidate()
        self.getAnnotation().setFontWeight(cssWeight)

    """*
    ** Specifies the color of the annotation's font.
    **
    **
    ** <p>
    ** For more information on standard CSS color
    ** specifications see the discussion in
    ** {@link Symbol#setBackgroundColor Symbol.setBackgroundColor}.
    ** <p>
    **
    ** @param cssColor color of the font used to display this
    **    point's annotation message.
    **
    ** @see #getAnnotationFontColor getAnnotationFontColor
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    *"""
    def setAnnotationFontColor(self, cssColor):
        self.getParent().invalidate()
        self.getAnnotation().setFontColor(cssColor)



    """*
    ** Specifies the CSS font-style used by this point's annotation
    ** message.
    **
    ** @param cssStyle any valid CSS font-style, namely,
    **   normal, italic, oblique, or inherit.
    **
    ** @see #getAnnotationFontStyle getAnnotationFontStyle
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    *"""
    def setAnnotationFontStyle(self, cssStyle):
        self.getParent().invalidate()
        self.getAnnotation().setFontStyle(cssStyle)

    """*
    ** Specifies the CSS font size of this point's annotation, in
    ** pixels.
    **
    ** @param fontSize the font size of this point's annotation, in
    **   pixels.
    **
    ** @see #getAnnotationFontSize getAnnotationFontSize
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    *"""
    def setAnnotationFontSize(self, fontSize):
        self.getParent().invalidate()
        self.getAnnotation().setFontSize(fontSize)

    """*
    ** Specifies the location, relative to this point's symbol,
    ** of this point's annotation (text label).
    ** <p>
    **
    ** You can further adjust the position of a point's
    ** annotation by specifying non-zero positional shifts via
    ** the <tt>setAnnotationXShift</tt> and
    ** <tt>setAnnotationYShift</tt> methods.
    **
    **
    ** @param annotationLocation the relative location of
    ** the annotation
    **
    ** @see #getAnnotationLocation getAnnotationLocation
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationVisible setAnnotationVisible
    **
    *"""
    def setAnnotationLocation(self, annotationLocation):
        self.getParent().invalidate()
        self.getAnnotation().setLocation(annotationLocation)


    """*
    ** Specifies the text of this point's annotation
    ** (label).
    ** <p>
    **
    ** <p>By default text is plain text, though
    ** you can change the size, weight, style, and color of
    ** the text via the <tt>setAnnotationFont*</tt>
    ** family of methods.
    **
    ** <p>
    **
    ** <b>To use HTML, <i>your text must begin with</i>
    ** <tt>&lt;html&gt</tt></b> (otherwise, GChart will treat
    ** it as plain text). Note that the leading
    ** <tt>&lt;html&gt</tt> is stripped off by GChart before
    ** your HTML gets to the browser. Since it's just a flag
    ** for GChart, not a real HTML tag, you should <i>not</i>
    ** use a closing <tt>&lt;/html&gt</tt> at the end.
    **
    ** <p> <small> The idea for adding HTML support (only plain
    ** text was supported originally) came from <a
    ** href="http:#groups.google.com/group/Google-Web-Toolkit/msg/cb89003dad2416fe">
    ** this GWT forum post by Malcolm Gorman</a>. The current
    ** HTML support (and, it's natural extension, Widget
    ** support) in tick labels and annotations, which seems so
    ** obvious in hindsight, might never have been added had it
    ** not been for this post. Thanks!</small>
    **
    ** <p>
    **
    ** <small><b>How to use the width and height upperbounds:</b>
    ** </small>
    **
    ** <p>
    **
    ** <blockquote><small>
    **
    **
    ** In most cases, you can safely ignore these two
    ** parameters, simply calling the {@link
    ** #setAnnotationText(String) 1-arg convenience method}
    ** and getting GChart to estimate them for you.
    ** <p>
    **
    ** The width and height upper-bounds define an invisible
    ** bounding box (a 1x1 GWT Grid, actualy) that is used to
    ** properly align and center your annotation.
    ** <p>
    **
    ** <p> Annotations can
    ** become misaligned if, say, due to the user zooming up
    ** their font size, an annotation's size exceeds these
    ** upperbounds. This misalignment problem can be fixed by
    ** specifying a larger width and/or height upperbound.
    ** But, larger upperbounds slow chart updates a bit.
    ** The defaults try to balance the performance and
    ** alignment tradeoff.
    ** <p>
    **
    ** There is one annoying but generally harmless side effect of
    ** using very large upperbounds: most browsers will extend their
    ** scroll regions to the right (and presumably below) the real
    ** page content so as to include the invisible bounding box. When
    ** this happens, it looks to the user as if there is a bunch of
    ** blank space on, say, the right edge of the page. In practice,
    ** I've always been able to prevent this problem simply by
    ** choosing at-least-somewhat-reasonably-tight upper bounds,
    ** though a little blank space may be unavoidable in some special
    ** cases.
    **
    ** </blockquote></small>
    **
    ** @param annotationText the text or (<tt>&lt;html&gt</tt>
    ** prefixed) HTML of this point's
    ** annotation, or <tt>None</tt> to remove all annotation.
    **
    ** @param widthUpperBound an upper bound on the width of
    ** the text or HTML, in pixels. Use <tt>NAI</tt> to
    ** get GChart to estimate this width using a heuristic
    ** that works fine most of the time.
    **
    ** @param heightUpperBound an upper bound on the height of
    ** the text or HTML, in pixels. Use <tt>NAI</tt> to
    ** get GChart to estimate this height using a heuristic
    ** that works fine most of the time.
    **
    ** @see #getAnnotationText getAnnotationText
    ** @see #setAnnotationText(String) setAnnotationText(String)
    ** @see #setAnnotationLocation setAnnotationLocation
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationWidget setAnnotationWidget
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationVisible setAnnotationVisible
    ** @see Axis#addTick(double,String,int,int) addTick
    **
    *"""
    def setAnnotationText(self, annotationText, 
                                widthUpperBound=NAI,
                                heightUpperBound=NAI):
        self.getParent().invalidate()
        self.getAnnotation().setText(annotationText,
                        widthUpperBound,
                        heightUpperBound)



    """*
    ** Specifies a widget defining this point's annotation
    ** <p>
    ** This method is similar to <tt>setAnnotationText</tt>
    ** except that it uses a widget, rather than a string
    ** to define this point's annotation.
    ** Although the string based method is faster
    ** on first chart rendering, and uses less memory, the
    ** widget-based method allows you to change the annotation
    ** independently of the chart--potentially bypassing (or
    ** at least speeding up) expensive chart updates later on.
    ** <p>
    **
    ** You might use a widget-based annotation to pop-up a
    ** message whenever the user clicks on a button underneath
    ** a particular data point on the chart, to include a small
    ** GWT <tt>Grid</tt> as a table embedded in the upper left
    ** hand corner of the chart, to trigger mouse-over events
    ** when the user hovers over a transparent image-based
    ** annotation centered on a particular point, etc.
    ** <p>
    **
    ** <i>Tip:</i>If you need to instrument a chart using
    ** widgets precisely positioned on the chart, but not
    ** associated with any visible curve, add a curve just to
    ** hold these annotations, with one point per annotation,
    ** and set that curve's symbol type
    ** to <tt>SymbolType.NONE</tt>.
    ** <p>
    **
    ** <b><i>Warning:</i></b> If you use the exact same widget
    ** reference to define two different annotations, GChart
    ** will render only one of them, and <i>there is no easy
    ** rule</i> that lets you reliably determine which one. So,
    ** don't do that.  Instead, if you want to use the same
    ** widget for two different annotations, use two identical
    ** but distinct copies of that widget. Similarly, if you
    ** want to move a single widget annotation from one point
    ** to another, be sure to "<tt>None</tt> out" the first
    ** point's annotation (e.g.  via
    ** <tt>setAnnotationWidget(None)</tt>) or the widget may
    ** not be rendered where you expect. You should also
    ** <tt>None</tt> out the annotation widget reference before
    ** moving the annotation widget to a position in the DOM
    ** completely outside of the GChart. A little extra
    ** bookkeeping on your part makes it possible to
    ** significantly simplify and streamline GChart's rendering
    ** algorithms.
    **
    *  @param annotationWidget the GWT Widget that defines this
    *    point's annotation.
    *
    *  @param widthUpperBound an upper bound on the width of
    *  the Widget, in pixels. If this and the next
    *  parameter are omitted, GChart will use
    *  <tt>DEFAULT_WIDGET_WIDTH_UPPERBOUND</tt>.
    *
    *  @param heightUpperBound an upper bound on the height of
    *  the Widget, in pixels. If this and the previous
    *  parameter are omitted, GChart will use <tt>
    *  DEFAULT_WIDGET_HEIGHT_UPPERBOUND</tt>
    *
    *
    * @see #getAnnotationWidget getAnnotationWidget
    * @see #setAnnotationText(String, int, int)
    *       setAnnotationText(String,int,int)
    * @see #setAnnotationWidget(Widget)
    * setAnnotationWidget(Widget)
    * @see #DEFAULT_WIDGET_HEIGHT_UPPERBOUND DEFAULT_WIDGET_HEIGHT_UPPERBOUND
    * @see #DEFAULT_WIDGET_WIDTH_UPPERBOUND DEFAULT_WIDGET_WIDTH_UPPERBOUND
    * @see SymbolType#NONE  SymbolType.NONE
    *
    *"""
    def setAnnotationWidget(self, annotationWidget,
                      widthUpperBound=DEFAULT_WIDGET_WIDTH_UPPERBOUND,
                      heightUpperBound=DEFAULT_WIDGET_HEIGHT_UPPERBOUND):
        self.getParent().invalidate()

        # accept "Not an Integer" (because setAnnotationText does)
        if widthUpperBound == NAI:
            widthUpperBound = DEFAULT_WIDGET_WIDTH_UPPERBOUND

        if heightUpperBound == NAI:
            heightUpperBound = DEFAULT_WIDGET_HEIGHT_UPPERBOUND

        self.getAnnotation().setWidget(annotationWidget,
                                        widthUpperBound,
                                        heightUpperBound)


    """*
    ** Specifies if this point's annotation
    ** (label) is visible or not.
    ** <p>
    **
    ** @param isVisible use True to make the annotation
    **   visible, or False to hide it.
    **
    ** @see #getAnnotationVisible getAnnotationVisible
    ** @see #setAnnotationLocation setAnnotationLocation
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationText setAnnotationText
    *"""
    def setAnnotationVisible(self, isVisible):
        self.getParent().invalidate()
        self.getAnnotation().setVisible(isVisible)




    """*
    ** Specifies the number of pixels (along the x-axis) to
    ** move this point's annotation from its default,
    ** <tt>AnnotationLocation</tt>-defined, position.  Negative
    ** values move the annotation in the negative x direction.
    **
    ** <p> For example, with the default <tt>xShift</tt> of 0,
    ** annotations with an <tt>AnnotationLocation</tt> of
    ** <tt>EAST</tt> will have their left edges flush against
    ** the right edge of, say, a box symbol representing the
    ** annotated point.  You could use an <tt>xShift</tt>
    ** setting of 10 to move the annotation 10 pixels to the
    ** right and thus introduce some space between the
    ** annotation and the box.
    ** <p>
    **
    ** <i>Special convention for pie slices:</i>
    ** Points on curves whose symbols represent pie
    ** slices always have the positive x-axis associated with
    ** the shifts specified by this method aligned with the
    ** outward-pointing pie radius that bisects the pie slice. This
    ** convention makes it easy to move pie slice annotations
    ** radially outward (via <tt>xShift > 0</tt>) or
    ** radially inward (via <tt>xShift < 0</tt>). For those
    ** rare situations where you may need to move a pie
    ** annotation perpendicularly to this radius, use
    ** <tt>setAnnotationYShift</tt>.
    **
    ** @param xShift number of pixels to move annotation
    **   along the x axis from
    **   it's default, <tt>AnnotationLocation</tt>-defined,
    **   location.
    **
    ** @see #setAnnotationYShift setAnnotationYShift
    ** @see #setAnnotationLocation setAnnotationLocation
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    ** @see #getAnnotationXShift getAnnotationXShift
    *"""
    def setAnnotationXShift(self, xShift):
        self.getParent().invalidate()
        self.getAnnotation().setXShift(xShift)

    """*
    ** Specifies the number of pixels (along the y-axis) to
    ** move this point's annotation from its default,
    ** <tt>AnnotationLocation</tt>-defined, position.  Negative
    ** values move the annotation in the negative y direction.
    **
    ** <p> For example, with the default <tt>yShift</tt> of 0,
    ** annotations with an <tt>AnnotationLocation</tt> of
    ** <tt>SOUTH</tt> will have their top edges flush against
    ** the bottom edge of, say, a box symbol representing the
    ** annotated point.  You could use a <tt>yShift</tt>
    ** setting of -10 to move the annotation down 10 pixels and
    ** thus introduce some spacing between the annotation and
    ** the box.
    ** <p>
    **
    ** <i>Special convention for pie slices:</i> The positive
    ** y-axis for pie slices always points one 90 degree
    ** counter-clockwise rotation from the direction of the
    ** outward-pointing pie radius that bisects the pie slice.
    ** This convention means that <tt>yShift</tt> moves pie
    ** slice annotations along a line <i>perpendicular to</i>
    ** this bisecting pie radius. Use the companion method
    ** <tt>setAnnotationXShift</tt> for the more common
    ** operation of moving the annotation along this bisecting
    ** radius.
    **
    ** @param yShift number of pixels to move annotation along
    **   the y-axis from it's default,
    **   <tt>AnnotationLocation</tt>-defined, location.
    **
    ** @see #setAnnotationXShift setAnnotationXShift
    ** @see #setAnnotationLocation setAnnotationLocation
    ** @see #setAnnotationFontWeight setAnnotationFontWeight
    ** @see #setAnnotationFontColor setAnnotationFontColor
    ** @see #setAnnotationFontStyle setAnnotationFontStyle
    ** @see #setAnnotationFontSize setAnnotationFontSize
    ** @see #setAnnotationText setAnnotationText
    ** @see #setAnnotationVisible setAnnotationVisible
    ** @see #getAnnotationXShift getAnnotationXShift
    *"""
    def setAnnotationYShift(self, yShift):
        self.getParent().invalidate()
        self.getAnnotation().setYShift(yShift)


    """*
    * Defines the x-coordinate of this point in "model units"
    * (arbitrary, application-specific, units mapped to the
    * horizontal dimension of the plot area).
    * <p>
    *
    * <tt>Double.NaN</tt>, <tt>Double.MAX_VALUE</tt>, and
    * <tt>-Double.MAX_VALUE</tt> have special meanings. See the
    * <tt>addPoint</tt> method for details.
    *
    *
    * @param x the x-coordinate of the point in model units.
    *
    ** @see #getX getX
    ** @see #setY setY
    ** @see #getY getY
    ** @see #addPoint addPoint
    """
    def setX(self, x):
        self.getParent().invalidate()
        self.x = x


    """*
    * Defines the y-coordinate of this point in "model units"
    * (arbitrary, application-specific, units mapped to the
    * vertical dimension of the plot area).
    * <p>
    *
    * <tt>Double.NaN</tt>, <tt>Double.MAX_VALUE</tt>, and
    * <tt>-Double.MAX_VALUE</tt> have special meanings. See the
    * <tt>addPoint</tt> method for details.
    *
    * @param y the y-coordinate of the point in model units.
    *
    ** @see #getX getX
    ** @see #setX setX
    ** @see #getY getY
    ** @see #addPoint addPoint
    **
    """
    def setY(self, y):
        self.getParent().invalidate()
        self.y = y


    def getAnnotation(self):
        if self.annotation is None:
            self.annotation = Annotation()

        return self.annotation

    """*
    * Retrieves the expanded hovertext associated with this
    * point.
    * <p>
    *
    * The expanded hovertext is obtained by replacing any
    * embedded parameters in the hovertext template with
    * their values as evaluated at this point. For example,
    * references to <tt>${x}</tt> and <tt>${y}</tt> in
    * the hovertext template are replaced with
    * appropriately formatted representations of this
    * point's x and y properties.
    * <p>
    *
    * By default, GChart will display this expanded hovertext
    * whenever the user "touches" a point with the
    * curve-specific, rectangular, mouse-centered, brush.
    * <p>
    *
    * <i>Tip:</i> To define your own custom parameter names
    * that can be embedded within hovertext templates and
    * will be interpreted/expanded relative to the touched point, use
    * the <tt>setHoverParameterInterpreter</tt> method.
    *
    * @return the expanded hover text associated with this point.
    *
    * @see Symbol#setHovertextTemplate setHovertextTemplate
    * @see #setHoverParameterInterpreter setHoverParameterInterpreter
    *
    """
    def getHovertext(self):
        return HovertextChunk.getHovertext(
                self.getParent().getSymbol().getHovertextChunks(), self)


 # end of class Point


