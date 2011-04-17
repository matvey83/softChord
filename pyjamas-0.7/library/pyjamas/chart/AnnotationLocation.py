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

from pyjamas.ui import HasHorizontalAlignment
from pyjamas.ui import HasVerticalAlignment

# Validates multipliers used to simplify computing the
# upper left corner location of symbols and labels to
# properly reflect their alignment relative to the
# plotted point or labeled symbol.
def validateMultipliers(widthMultiplier, heightMultiplier):
    if (not (widthMultiplier == 0  or  abs(widthMultiplier)==1)  and
        not (heightMultiplier == 0  or abs(heightMultiplier)==1)):
        raise IllegalArgumentException(
        "widthMultiplier, heightMultiplier args must both be " +
        "either 0, 1, or -1")

# retrieves a location given its multipliers
def getAnnotationLocation(widthMultiplier, heightMultiplier):
    locationMap = [
        [NORTHWEST, NORTH, NORTHEAST],
        [WEST, CENTER, EAST],
        [SOUTHWEST, SOUTH, SOUTHEAST]]
    # assumes both multiplier are -1, 0, or 1
    result = locationMap[heightMultiplier+1][widthMultiplier+1]
    return result
    
    
# Negative width or height "turn the symbol inside-out",
# requiring a corresponding "reflection" of annotation
# location (only needed for baseline-based bar symbols)
def transform(a, signWidth, signHeight):
    result = a
    if signWidth < 0  or  signHeight < 0:
        result = getAnnotationLocation(
                    signWidth*a.widthMultiplier,
                    signHeight*a.heightMultiplier)
    
    return result


"""*
** Defines the location of a data point's annotation or hover
** annotation (which can be defined by either plain text, HTML,
** or a widget) relative to the location of that point's
** symbol.  The "Field Summary"
** section below lists all available annotation locations.
** <p>
**
** The default annotation location is {@link
** AnnotationLocation#SOUTH SOUTH} for annotations and
** is symbol-type-dependent for hover annotations. See the
** <tt>setHoverLocation</tt> method for list of these defaults.
**
** <p>
**
** You can further adjust the position of a point's
** annotation (or hover annotation) by specifying non-zero
** positional shifts via the <tt>setAnnotationXShift</tt>
** and <tt>setAnnotationYShift</tt> (or via the
** <tt>setHoverXShift</tt>, <tt>setHoverYShift</tt>),
** and <tt>setHoverAnnotationSymbolType</tt> methods for
** hover annotations).
** <p>
**
** @see Curve.Point#setAnnotationLocation Point.setAnnotationLocation
** @see Curve.Point#setAnnotationXShift Point.setAnnotationXShift
** @see Curve.Point#setAnnotationYShift Point.setAnnotationYShift
** @see Symbol#setHoverLocation Symbol.setHoverLocation
** @see Symbol#setHoverAnnotationSymbolType
** Symbol.setHoverAnnotationSymbolType
** @see Symbol#setHoverXShift Symbol.setHoverXShift
** @see Symbol#setHoverYShift Symbol.setHoverYShift
** @see #DEFAULT_HOVER_LOCATION DEFAULT_HOVER_LOCATION
**
*"""
class AnnotationLocation:
    
    # these multiply the width and height of the annotation and
    # the symbol it is attached to in order to define the
    # center of the annotation (see equations in later code),
    # and thus the upper left corner anchoring point.
    def __init__(self, widthMultiplier, heightMultiplier):
        validateMultipliers(widthMultiplier, heightMultiplier)
        self.widthMultiplier = widthMultiplier
        self.heightMultiplier = heightMultiplier
    
    # These define the alignment of the label within it's
    # containing 1 x 1 Grid. For example, if this
    # containing grid is to the left of the labeled
    # symbol (widthMultiplier==-1) the horizontal
    # alignment will be ALIGN_RIGHT, so as to bring the
    # contained label flush against the left edge of the
    # labeled symbol.
    def getHorizontalAlignment(self):
        if self.widthMultiplier == -1:
            result = HasHorizontalAlignment.ALIGN_RIGHT
        
        elif self.widthMultiplier == 0:
            result = HasHorizontalAlignment.ALIGN_CENTER
        
        elif self.widthMultiplier == 1:
            result = HasHorizontalAlignment.ALIGN_LEFT
        
        else:
            raise IllegalStateException(
                    "Invalid widthMultiplier: " + str(self.widthMultiplier) +
                    " 1, 0, or -1 were expected.")
        
        return result
    
    
    """ Given the x-coordinate at the center of the symbol
    * that this annotation annotates, the annotation's
    * width, and the symbol's width, this method returns
    * the x-coordinate of the upper left corner of
    * this annotation.
    """
    def getUpperLeftX(self, x, w, symbolW):
        result = int (round(x +
                    (self.widthMultiplier * (w + symbolW) - w)/2.) )
        return result
    
    
    """ analogous to getUpperLeftX, except for the y-coordinate """
    def getUpperLeftY(self, y, h, symbolH):
        result = int (round(y +
                    (self.heightMultiplier * (h + symbolH) - h)/2.))
        return result
    
    # analogous to getHorizontalAlignment
    def getVerticalAlignment(self):
        if self.heightMultiplier == -1:
            result = HasVerticalAlignment.ALIGN_BOTTOM
        
        elif self.heightMultiplier == 0:
            result = HasVerticalAlignment.ALIGN_MIDDLE
        
        elif self.heightMultiplier == 1:
            result = HasVerticalAlignment.ALIGN_TOP
        
        else:
            raise IllegalStateException(
            "Invalid heightMultiplier: " + self.heightMultiplier +
            " -1, 0, or 1 were expected.")
        
        return result
    
    
    
    """
    * This method returns the annotation location whose
    * "attachment point" keeps the annotation either
    * completely outside, centered on, or completely inside
    * (depending on if the heightMultiplier of this annotation
    * is 1, 0, or -1) the point on the pie's circumference
    * associated with the given angle.
    * <p>
    *
    * The use of heightMultiplier rather than widthMultiplier
    * is somewhat arbitrary, but was chosen so that the
    * NORTH, CENTER, and SOUTH annotation locations have the
    * same interpretation for a pie slice whose bisecting
    * radius points due south (due south is the default initial
    * pie slice orientation) and for a 1px x 1px BOX_CENTER
    * type symbol positioned at the due south position on the
    * pie's circumference. As the pie-slice-arc-bisection
    * point moves clockwise around the pie perimeter, the
    * attachment point (except for vertically-centered
    * annotations, which remain centered on the pie arc) also
    * moves clockwise, but in discrete jumps (e.g. from
    * NORTH, to NORTHEAST, to EAST, to SOUTHEAST, to SOUTH,
    * etc. for annotations inside the pie) so the annotation
    * remains appropriately attached to the center of the
    * slice's arc as the angle changes.
    *
    """
    def decodePieLocation(self, thetaMid):
        # a sin or cos that is small enough so that the
        # associated angle is horizontal (for sines) or vertical
        # (for cosines) enough to warrant use of a "centered"
        # annotation location.
        LOOKS_VERTICAL_OR_HORIZONTAL_DELTA = 0.1
        sinTheta = math.sin(thetaMid)
        cosTheta = math.cos(thetaMid)
        if cosTheta < -LOOKS_VERTICAL_OR_HORIZONTAL_DELTA:
            pieTransformedWidthMultiplier = -self.heightMultiplier
        elif cosTheta > LOOKS_VERTICAL_OR_HORIZONTAL_DELTA:
            pieTransformedWidthMultiplier = self.heightMultiplier
        else:
            pieTransformedWidthMultiplier = 0
        # XXX ?? surely this should be widthMultiplier?
        if sinTheta < -LOOKS_VERTICAL_OR_HORIZONTAL_DELTA:
            pieTransformedHeightMultiplier = -self.heightMultiplier
        elif sinTheta > LOOKS_VERTICAL_OR_HORIZONTAL_DELTA:
            pieTransformedHeightMultiplier = self.heightMultiplier
        else:
            pieTransformedHeightMultiplier = 0
        
        return getAnnotationLocation(pieTransformedWidthMultiplier,
                                pieTransformedHeightMultiplier)
        
    
    
 # end of class AnnotationLocation
    
# non-tagging-only locations used by ANCHOR_MOUSE_* symbol types
AT_THE_MOUSE = AnnotationLocation(0,0)
AT_THE_MOUSE_SNAP_TO_X = AnnotationLocation(0,0)
AT_THE_MOUSE_SNAP_TO_Y = AnnotationLocation(0,0)
"""*
** Specifies that a point's annotation (label) should
** be positioned so as to be centered on the symbol
** used to represent the point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
CENTER = AnnotationLocation(0,0)

north = AnnotationLocation(0,-1)
west = AnnotationLocation(-1, 0)
south = AnnotationLocation(0, 1)

"""*
** Specifies that a point's annotation (label) should be
** placed just above, and centered horizontally on,
** vertical bars that grow down from a horizontal
** baseline, and just below, and centered horizontally on,
** vertical bars that grow up from a horizontal baseline.
**
** <p>
**
** This another name for
** <tt>AnnotationLocation.NORTH</tt>. Its sole purpose is
** to clarify/document the behavior of this location type
** when used in conjunction with curves that employ
** <tt>VBAR_BASELINE_*</tt> symbol types.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see SymbolType#VBAR_BASELINE_CENTER SymbolType.VBAR_BASELINE_CENTER
**
*"""
CLOSEST_TO_HORIZONTAL_BASELINE = north

"""*
** Specifies that a point's annotation (label) should be
** placed just to the right of, and centered vertically
** on, horizontal bars that grow left from a vertical
** baseline, and just to the left of, and centered
** vertically on, horizontal bars that grow right from a
** vertical baseline.
**
** <p>
**
** This another name for
** <tt>AnnotationLocation.WEST</tt>. Its sole purpose is
** to clarify/document the behavior of this location type
** when used in conjunction with curves that employ the
** <tt>HBAR_BASELINE_*</tt> symbol types.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see SymbolType#HBAR_BASELINE_CENTER SymbolType.HBAR_BASELINE_CENTER
**
*"""

CLOSEST_TO_VERTICAL_BASELINE = west

"""*
** Specifies that a point's annotation (label) should
** be positioned just to the right of, and vertically
** centered on, the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation
*"""
EAST = AnnotationLocation(1, 0)

"""*
** Specifies that a point's annotation (label) should be
** placed just below, and centered horizontally on,
** vertical bars that grow down from a horizontal
** baseline, and just above, and centered horizontally on,
** vertical bars that grow up from a horizontal baseline.
**
** <p>
**
** This another name for
** <tt>AnnotationLocation.SOUTH</tt>. Its sole purpose is
** to clarify/document the behavior of this location type
** when used in conjunction with curves that employ
** <tt>VBAR_BASELINE_*</tt> symbol types.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see SymbolType#VBAR_BASELINE_CENTER SymbolType.VBAR_BASELINE_CENTER
**
*"""
FARTHEST_FROM_HORIZONTAL_BASELINE = south

"""*
** Specifies that a point's annotation (label) should be
** placed just to the left of, and centered vertically on,
** horizontal bars that grow left from a vertical
** baseline, and just to the right of, and centered
** vertically on, horizontal bars that grow right from a
** vertical baseline.
**
** <p>
**
** This another name for
** <tt>AnnotationLocation.EAST</tt>. Its sole purpose is
** to clarify/document the behavior of this location type
** when used in conjunction with curves that employ the
** <tt>HBAR_BASELINE_*</tt> family of symbol types.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see SymbolType#HBAR_BASELINE_CENTER SymbolType.HBAR_BASELINE_CENTER
**
*"""
FARTHEST_FROM_VERTICAL_BASELINE = EAST


"""*
** Specifies that a point's annotation (label) should
** be positioned just inside, and centered on, the
** arc side of a pie slice.
** <p>
**
** You can move a pie slice's annotation a specific number
** of pixels radially away from (or towards) the pie
** center by passing a positive (or negative) argument to
** the associated <tt>Point</tt>'s
** <tt>setAnnotationXShift</tt> method.
**
** <p> This is pie-friendly synonym for, and when used
** with non-pie symbol types will behave exactly the same
** as, <tt>AnnotationLocation.NORTH</tt>
**
** @see #OUTSIDE_PIE_ARC OUTSIDE_PIE_ARC
** @see #ON_PIE_ARC ON_PIE_ARC
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see AnnotationLocation#NORTH NORTH
*"""
INSIDE_PIE_ARC = north

"""*
** Specifies that a point's annotation (label) should
** be positioned just above, and horizontally centered on,
** the symbol used to represent the point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
NORTH = north


"""*
** Specifies that a point's annotation (label) should
** be positioned just to the right of and above,
** the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation
*"""
NORTHEAST = AnnotationLocation(1, -1)

"""*
** Specifies that a point's annotation (label) should
** be positioned just to the left of and above,
** the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation
*"""
NORTHWEST = AnnotationLocation(-1, -1)


"""*
** Specifies that a point's annotation (label) should
** be centered on the center-point of the
** arc side of a pie slice.
** <p>
**
** You can move a pie slice's annotation a specific number
** of pixels radially away from (or towards) the pie
** center by passing a positive (or negative) argument to
** the associated <tt>Point</tt>'s
** <tt>setAnnotationXShift</tt> method.
**
**
**
** <p> This is pie-friendly synonym for, and when used
** with non-pie symbol types will behave exactly the same
** as, <tt>AnnotationLocation.CENTER</tt>
**
** @see #OUTSIDE_PIE_ARC OUTSIDE_PIE_ARC
** @see #INSIDE_PIE_ARC INSIDE_PIE_ARC
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see AnnotationLocation#CENTER CENTER
**
*"""
ON_PIE_ARC = CENTER

"""*
** Specifies that a point's annotation (label) should
** be positioned just outside, and centered on, the
** arc side of a pie slice.
** <p>
**
** You can move a pie slice's annotation a specific number
** of pixels radially away from (or towards) the pie
** center by passing a positive (or negative) argument to
** the associated <tt>Point</tt>'s
** <tt>setAnnotationXShift</tt> method.
**
** <p> This is pie-friendly synonym for, and when used
** with non-pie symbol types will behave exactly the same
** as, <tt>AnnotationLocation.SOUTH</tt>
**
** @see #INSIDE_PIE_ARC INSIDE_PIE_ARC
** @see #ON_PIE_ARC ON_PIE_ARC
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
** @see Curve.Point#setAnnotationXShift setAnnotationXShift
** @see AnnotationLocation#SOUTH SOUTH
*"""
OUTSIDE_PIE_ARC = south

"""*
** Specifies that a point's annotation (label) should
** be positioned just below, and horizontally centered on,
** the symbol used to represent the point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
SOUTH = south


"""*
** Specifies that a point's annotation (label) should
** be positioned just to the right of and below,
** the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
SOUTHEAST = AnnotationLocation(1, 1)
"""*
** Specifies that a point's annotation (label) should
** be positioned just to the left of and below,
** the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
SOUTHWEST = AnnotationLocation(-1, 1)

"""*
** Specifies that a point's annotation (label) should
** be positioned just to the left of, and vertically
** centered on, the symbol used to represent the
** point.
**
** @see Curve.Point#setAnnotationLocation setAnnotationLocation
*"""
WEST = west


