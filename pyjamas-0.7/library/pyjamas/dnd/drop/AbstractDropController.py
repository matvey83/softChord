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


from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd import DragController
from pyjamas.dnd import DragEndEvent
from pyjamas.dnd import VetoDragException

"""*
* Base class for typical drop controllers. Contains some basic functionality
* like adjust widget styles.
"""
abstract class AbstractDropController implements DropController:
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    String CSS_DROP_TARGET_ENGAGE
    
    String CSS_DROP_TARGET = "dragdrop-dropTarget"
    String PRIVATE_CSS_DROP_TARGET_ENGAGE = "dragdrop-dropTarget-engage"
    
    {
        CSS_DROP_TARGET_ENGAGE = PRIVATE_CSS_DROP_TARGET_ENGAGE
    
    
    Widget dropTarget
    
    def __init__(self, dropTarget):
        self.dropTarget = dropTarget
        dropTarget.addStyleName(CSS_DROP_TARGET)
    
    
    """*
    * @deprecated No longer a part of the API.
    """
    def getCurrentDragController(self):
        raise UnsupportedOperationException()
    
    
    def getDropTarget(self):
        return dropTarget
    
    
    """*
    * @deprecated Never part of the released API.
    """
    def getDropTargetEngageStyleName(self):
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated No longer a part of the API.
    """
    def getDropTargetStyleName(self):
        raise UnsupportedOperationException()
    
    
    def onDrop(self, context):
    
    
    def onDrop(self, reference, draggable, dragController):
        raise UnsupportedOperationException()
    
    
    def onEnter(self, context):
        dropTarget.addStyleName(PRIVATE_CSS_DROP_TARGET_ENGAGE)
    
    
    def onEnter(self, reference, draggable, dragController):
        raise UnsupportedOperationException()
    
    
    def onLeave(self, context):
        dropTarget.removeStyleName(PRIVATE_CSS_DROP_TARGET_ENGAGE)
    
    
    def onLeave(self, draggable, dragController):
        raise UnsupportedOperationException()
    
    
    def onLeave(self, reference, draggable, dragController):
        raise UnsupportedOperationException()
    
    
    def onMove(self, context):
    
    
    void onMove(int x, int y, Widget reference, Widget draggable,
    DragController dragController) {
        raise UnsupportedOperationException()
    
    
    def onMove(self, reference, draggable, dragController):
        raise UnsupportedOperationException()
    
    
    void onPreviewDrop(DragContext context) throws VetoDragException {
    
    
    """*
    * @deprecated Use {@link #onPreviewDrop(DragContext)} instead.
    """
    void onPreviewDrop(Widget reference, Widget draggable, DragController dragController)
    throws VetoDropException {
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated No longer a part of the API.
    """
    def makeDragEndEvent(self, context):
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated No longer a part of the API.
    """
    DragEndEvent makeDragEndEvent(Widget reference, Widget draggable,
    DragController dragController) {
        raise UnsupportedOperationException()
    


