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




from pyjamas import DOM
from pyjamas import Window



























from pyjamas.ui  import Event
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


from pyjamas.chart import SymbolType


"""*
** Defines keywords <tt>INSIDE</tt>, <tt>OUTSIDE</tt>, and
** <tt>CENTERED</tt> that specify the location of ticks
** relative to their axis.
** <p>
**
** @see Axis#setTickLocation setTickLocation
**
*"""
class TickLocation:
    """
    * An integer form of the tick location (-1 - OUTSIDE,
    * 0 - CENTERED, +1 - INSIDE) that facilitates
    * generating appropriate symbol types for rendering ticks
    *
    """
    def __init__(self, locationIndex):
        self.locationIndex = locationIndex
    
    # symbol type representing ticks on x axes at given position
    # axisPosition of  -1 is x-axis, +1 is x2-axis.
    #
    # (symbols representing ticks depend on the axis they are on)
    def getXAxisSymbolType(self, axisPosition):
        symbolMap = [SymbolType.BOX_NORTH, SymbolType.BOX_CENTER, SymbolType.BOX_SOUTH]
        result = symbolMap[axisPosition*self.locationIndex+1]
        return result
    
    # symbol type representing ticks on y axes at given position
    # axisPosition of  -1 is y-axis, +1 is y2-axis
    #
    # (symbols representing ticks depend on the axis they are on)
    def getYAxisSymbolType(self, axisPosition):
        symbolMap = [SymbolType.BOX_EAST, SymbolType.BOX_CENTER, SymbolType.BOX_WEST]
        result = symbolMap[axisPosition*self.locationIndex+1]
        return result
    
    
 # class TickLocation

"""*
** Indicates that ticks are located outside of the axis.
**
** @see Axis#setTickLocation setTickLocation
*"""
OUTSIDE = TickLocation(-1)
"""*
** Indicates that ticks are centered on the axis.
**
** @see Axis#setTickLocation setTickLocation
*"""
CENTERED = TickLocation(0)
"""*
** Indicates that ticks are located inside of the axis.
**
** @see Axis#setTickLocation setTickLocation
*"""
INSIDE = TickLocation(1)


"""*
* The default tick location.
*
* @see Axis#setTickLocation setTickLocation
"""
DEFAULT_TICK_LOCATION = OUTSIDE


