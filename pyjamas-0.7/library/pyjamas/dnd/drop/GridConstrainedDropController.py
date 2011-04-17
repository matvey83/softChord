"""
* Copyright 2007 Fred Sauer
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


from pyjamas.ui.AbsolutePanel import AbsolutePanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext

from AbsolutePositionDropController import AbsolutePositionDropController

import math

"""*
* A {@link DropController} which constrains the placement of draggable widgets
* the grid specified in the constructor.
"""
class GridConstrainedDropController(AbsolutePositionDropController):
    
    def __init__(self, dropTarget, gridX, gridY):
        super(dropTarget)
        self.gridX = gridX
        self.gridY = gridY
    
    
    def drop(self, widget, left, top):
        left = math.max(0, math.min(left, dropTarget.getOffsetWidth() - widget.getOffsetWidth()))
        top = math.max(0, math.min(top, dropTarget.getOffsetHeight() - widget.getOffsetHeight()))
        left = math.round(float( left ) / gridX) * gridX
        top = math.round(float( top ) / gridY) * gridY
        dropTarget.add(widget, left, top)
    
    
    def onMove(self, context):
        super.onMove(context)
        for iterator in draggableList:
            draggable = iterator.next()
            draggable.desiredX = context.desiredDraggableX - dropTargetOffsetX + draggable.relativeX
            draggable.desiredY = context.desiredDraggableY - dropTargetOffsetY + draggable.relativeY
            draggable.desiredX = math.max(0, math.min(draggable.desiredX, dropTargetClientWidth
            - draggable.offsetWidth))
            draggable.desiredY = math.max(0, math.min(draggable.desiredY, dropTargetClientHeight
            - draggable.offsetHeight))
            draggable.desiredX = math.round(float( draggable.desiredX ) / gridX) * gridX
            draggable.desiredY = math.round(float( draggable.desiredY ) / gridY) * gridY
            dropTarget.add(draggable.positioner, draggable.desiredX, draggable.desiredY)
        
    


