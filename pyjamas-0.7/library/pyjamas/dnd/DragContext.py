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


from pyjamas.ui.AbsolutePanel import AbsolutePanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.drop import DropController




"""*
* Container class for context information about the current drag operation.
"""
class DragContext:
    """*
    * TODO replace context.dragController.getBoundaryPanel() with context.boundaryPanel
    """
    self.boundaryPanel
    
    """*
    * Desired x coordinate of draggable due to mouse dragging.
    """
    self.desiredDraggableX=0
    
    """*
    * Desired y coordinate of draggable due to mouse dragging.
    """
    self.desiredDraggableY
    
    """*
    * The DragController for which this context exists.
    """
    self.dragController
    
    """*
    * The primary widget currently being dragged or <code>None</code> when not dragging.
    """
    self.draggable
    
    """*
    * The currently engaged drop controller or <code>None</code> when not dragging,
    * or when the drag controller does not utilize drop controllers.
    """
    self.dropController
    
    """*
    * The drop controller which participated in the drop, or <code>None</code>
    * before the drop has occurred, or when the drag controller does not utilize
    * drop controllers.
    """
    self.finalDropController
    
    """*
    * Current mouse x coordinate.
    """
    self.mouseX
    
    """*
    * Current mouse y coordinate.
    """
    self.mouseY
    
    """*
    * List of currently selected widgets. List will contain at most
    * one widget when {@link DragController#setBehaviorMultipleSelection(boolean)}
    * is disabled.
    """
    self.selectedWidgets = []
    
    """*
    * At the end of a drag operation this fields will contain either the
    * {@link VetoDragException} which caused the drag to be cancelled, or
    * <code>None</code> if the drag was successful. Note that while the
    * value of this field will still be <code>None</code> in
    * {@link DragHandler#onPreviewDragEnd(DragEndEvent)}, the value will
    * be available in {@link DragHandler#onDragEnd(DragEndEvent)}.
    """
    self.vetoException
    
    def __init__(self, dragController):
        self.dragController = dragController
        boundaryPanel = dragController.getBoundaryPanel()
    
    
    """*
    * Called by {@link MouseDragHandler#dragEndCleanup} at the end of a drag operation
    * to cleanup state.
    """
    def dragEndCleanup(self):
        dropController = None
        draggable = None
    
    
    """*
    * Called by {@link MouseDragHandler#startDragging} at the start of a drag operation
    * to initialize state.
    """
    def dragStartCleanup(self):
        assert dropController is None
        finalDropController = None
        vetoException = None
    


