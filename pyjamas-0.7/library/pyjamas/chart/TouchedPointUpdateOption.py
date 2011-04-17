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


"""*
* Defines how the <tt>update</tt> method updates the touched
* point, that is, the point the user is considered to be
* hovered over.
*
* @see #update(TouchedPointUpdateOption) update
*
"""

class TouchedPointUpdateOption(object):
    def __init__(self):
        pass
    
"""*
* When this option is passed to the update method, any
* touched point is cleared as a consequence of the update.
* <p>
*
* This option can be used when you want to "start fresh"
* with regards to hover feedback after an update, and want
* to assure that only explicit user-generated mouse move
* actions (rather than objects moving <i>underneath</i> a
* fixed-position mouse cursor) can trigger hover feedback.
*
* @see #update update
* @see #TOUCHED_POINT_LOCKED TOUCHED_POINT_LOCKED
* @see #TOUCHED_POINT_UPDATED TOUCHED_POINT_UPDATED
*
"""
TOUCHED_POINT_CLEARED = TouchedPointUpdateOption()

"""*
* When this option is passed to the update method, any
* previously touched point is locked in (remains unchanged).
* <p>
*
* For example, if the mouse is over a certain point before
* the update, and that point moves away from the mouse
* (without the mouse moving otherwise) as a consequence of
* the update, the hover feedback remains "locked in" to the
* original point, even though the mouse is no longer on top
* of that point.
* <p>
*
* This option is useful for hover widgets that modify the
* position, size, symbol of points/curves, and do not want the
* selected point/curve (and popup hover widget) to change as
* a consequence of such changes.
* <p>
*
* <i>Note:</i> If the currently touched point or the curve
* containing it is deleted, GChart sets the touched point
* reference to <tt>None</tt>. In that case, this option and
* <tt>TOUCHED_POINT_CLEARED</tt> behave the same way.
*
*
* @see #update update
* @see #TOUCHED_POINT_CLEARED TOUCHED_POINT_CLEARED
* @see #TOUCHED_POINT_UPDATED TOUCHED_POINT_UPDATED
*
"""
TOUCHED_POINT_LOCKED = TouchedPointUpdateOption()
"""*
* When this option is passed to the update method, the
* touched point is updated so that it reflects whatever point
* is underneath the mouse cursor after the update
* completes.
* <p>
*
* For example, if the mouse is not hovering over any point
* before the update, but the update repositions one of the
* points so that it is now underneath the mouse cursor,
* the hover feedback for that point will be displayed.
* Similarly, if the update moves a point away from the
* mouse cursor, previously displayed hover feedback will
* be eliminated.
* <p>
*
* @see #update update
* @see #TOUCHED_POINT_CLEARED TOUCHED_POINT_CLEARED
* @see #TOUCHED_POINT_LOCKED TOUCHED_POINT_LOCKED
*
"""
TOUCHED_POINT_UPDATED = TouchedPointUpdateOption()



