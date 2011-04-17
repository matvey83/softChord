"""
* Copyright 2008 Fred Sauer
*
* Licensed under the Apache License, Version 2.0 (the "License"); you may not
* use this file except in compliance with the License. You may obtain a copy of
* the License at
*
* http:#www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
* License for the specific language governing permissions and limitations under
* the License.
"""


from pyjamas import DOM

from pyjamas.ui.Panel import Panel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.drop import DropController
from pyjamas.dnd.util import Area
from pyjamas.dnd.util import CoordinateLocation
from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import Location
from pyjamas.dnd.util import WidgetArea





"""*
* Package helper implementation class for {@link AbstractDragController}
* to track all relevant {@link DropController DropControllers}.
"""
class DropControllerCollection:
    class Candidate implements Comparable:
        DropController dropController
        Area targetArea
        
        def __init__(self, dropController):
            self.dropController = dropController
            Widget target = dropController.getDropTarget()
            if not target.isAttached():
                raise IllegalStateException(
                "Unattached drop target. You must call DragController#unregisterDropController for all drop targets not attached to the DOM.")
            
            targetArea = WidgetArea(target, None)
        
        
        def compareTo(self, arg0):
            Candidate other = (Candidate) arg0
            
            Element myElement = getDropTarget().getElement()
            Element otherElement = other.getDropTarget().getElement()
            if DOM.compare(myElement, otherElement):
                return 0
             elif DOM.isOrHasChild(myElement, otherElement):
                return -1
             elif DOM.isOrHasChild(otherElement, myElement):
                return 1
             else:
                return 0
            
        
        
        def getDropController(self):
            return dropController
        
        
        def getDropTarget(self):
            return dropController.getDropTarget()
        
        
        def getTargetArea(self):
            return targetArea
        
    
    
    ArrayList dropControllerList
    Candidate[] sortedCandidates = None
    
    """*
    * Default constructor.
    """
    def __init__(self, dropControllerList):
        self.dropControllerList = dropControllerList
    
    
    """*
    * Determines which DropController represents the deepest DOM descendant
    * drop target located at the provided location <code>(x, y)</code>.
    *
    * @param x offset left relative to document body
    * @param y offset top relative to document body
    * @return a drop controller for the intersecting drop target or <code>None</code> if none
    *         are applicable
    """
    def getIntersectDropController(self, x, y):
        Location location = CoordinateLocation(x, y)
        for int i = sortedCandidates.length - 1; i >= 0; i--:
            Candidate candidate = sortedCandidates[i]
            Area targetArea = candidate.getTargetArea()
            if targetArea.intersects(location):
                return candidate.getDropController()
            
        
        return None
    
    
    """*
    * Cache a list of eligible drop controllers, sorted by relative DOM positions
    * of their respective drop targets. Called at the beginning of each drag operation,
    * or whenever drop target eligibility has changed while dragging.
    *
    * @param boundaryPanel boundary area for drop target eligibility considerations
    * @param context the current drag context
    """
    def resetCache(self, boundaryPanel, context):
        ArrayList list = ArrayList()
        
        if context.draggable is not None:
            WidgetArea boundaryArea = WidgetArea(boundaryPanel, None)
            for Iterator iterator = dropControllerList.iterator(); iterator.hasNext();:
                DropController dropController = (DropController) iterator.next()
                Candidate candidate = Candidate(dropController)
                if DOMUtil.isOrContains(context.draggable.getElement(),
                candidate.getDropTarget().getElement())) {
                    continue
                
                if candidate.getTargetArea().intersects(boundaryArea):
                    list.add(candidate)
                
            
        
        
        sortedCandidates = (Candidate[]) list.toArray(Candidate[list.size()])
        Arrays.sort(sortedCandidates)
    


