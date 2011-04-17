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

from pyjamas.dnd.drop import BoundaryDropController
from pyjamas.dnd.drop import DropController




"""*
* {@link DragController} which performs the bare essentials such as
* adding/removing styles, maintaining collections, adding mouse listeners, etc.
*
* <p>
* Extend this class to implement specialized drag capabilities such table
* column or panel resizing. For classic drag-and-drop functionality, i.e. the
* ability to pickup, move around and drop widgets, use
* {@link PickupDragController}.
* </p>
"""
class AbstractDragController implements DragController:
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    self.CSS_DRAGGABLE
    
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    self.CSS_DRAGGING
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    self.CSS_HANDLE
    
    self.CSS_SELECTED = "dragdrop-selected"
    
    dragHandles = HashMap()
    
    self.PRIVATE_CSS_DRAGGABLE = "dragdrop-draggable"
    self.PRIVATE_CSS_DRAGGING = "dragdrop-dragging"
    self.PRIVATE_CSS_HANDLE = "dragdrop-handle"
    
    def setVersion(self):

    self.CSS_DRAGGABLE = PRIVATE_CSS_DRAGGABLE
    self.CSS_DRAGGING = PRIVATE_CSS_DRAGGING
    self.CSS_HANDLE = PRIVATE_CSS_HANDLE
    
    
    def setVersion(self):
        JS("""
        $GWT_DND_VERSION = "2.0.7";
        """)
    
    
    self.context
    self.boundaryPanel
    self.constrainedToBoundaryPanel=False
    self.dragEndEvent
    self.dragHandlers
    self.dragStartEvent
    self.dragStartPixels=0
    self.mouseDragHandler
    self.multipleSelectionAllowed = False
    
    """*
    * Create a drag-and-drop controller. Drag operations will be limited to
    * the specified boundary panel.
    *
    * @param boundaryPanel the desired boundary panel or <code>RootPanel.get()</code>
    *                      if entire document body is to be the boundary
    """
    def __init__(self, boundaryPanel):
        assert boundaryPanel is not None : "Use 'RootPanel.get()' instead of 'None'."
        self.boundaryPanel = boundaryPanel
        context = DragContext(this)
        mouseDragHandler = MouseDragHandler(context)
    
    
    def addDragHandler(self, handler):
        if dragHandlers is None:
            dragHandlers = DragHandlerCollection()
        
        dragHandlers.add(handler)
    
    
    def clearSelection(self):
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext():
            widget = (Widget) iterator.next()
            widget.removeStyleName(CSS_SELECTED)
            iterator.remove()
        
    
    
    def dragEnd(self):
        context.draggable.removeStyleName(PRIVATE_CSS_DRAGGING)
        if dragHandlers is not None:
            dragHandlers.fireDragEnd(dragEndEvent)
            dragEndEvent = None
        
        assert dragEndEvent is None
    
    
    def dragEnd(self, draggable, dropTarget):
        raise UnsupportedOperationException()
    
    
    def dragStart(self):
        resetCache()
        if dragHandlers is not None:
            dragHandlers.fireDragStart(dragStartEvent)
            dragStartEvent = None
        
        context.draggable.addStyleName(PRIVATE_CSS_DRAGGING)
        assert dragStartEvent is None
    
    
    def dragStart(self, draggable):
        raise UnsupportedOperationException()
    
    
    def getBehaviorConstrainedToBoundaryPanel(self):
        return constrainedToBoundaryPanel
    
    
    def getBehaviorDragStartSensitivity(self):
        return dragStartPixels
    
    
    def getBehaviorMultipleSelection(self):
        return multipleSelectionAllowed
    
    
    def getBoundaryPanel(self):
        return boundaryPanel
    
    
    def getDropControllerCollection(self):
        raise UnsupportedOperationException()
    
    
    def getIntersectDropController(self, widget):
        raise UnsupportedOperationException()
    
    
    def getIntersectDropController(self, widget, x, y):
        raise UnsupportedOperationException()
    
    
    def getMovableWidget(self):
        raise UnsupportedOperationException()
    
    
    """*
    * Attaches a {@link MouseDragHandler} (which is a
    * {@link com.google.gwt.user.client.ui.MouseListener}) to the widget,
    * applies the {@link #PRIVATE_CSS_DRAGGABLE} style to the draggable, applies the
    * {@link #PRIVATE_CSS_HANDLE} style to the handle.
    *
    * @see #makeDraggable(Widget, Widget)
    * @see HasDragHandle
    *
    * @param draggable the widget to be made draggable
    """
    def makeDraggable(self, draggable):
        if draggable instanceof HasDragHandle:
            makeDraggable(draggable, ((HasDragHandle) draggable).getDragHandle())
         else:
            makeDraggable(draggable, draggable)
        
    
    
    """*
    * Similar to {@link #makeDraggable(Widget)}, but allow separate, child to be
    * specified as the drag handle by which the first widget can be dragged.
    *
    * @param draggable the widget to be made draggable
    * @param dragHandle the widget by which widget can be dragged
    """
    def makeDraggable(self, draggable, dragHandle):
        mouseDragHandler.makeDraggable(draggable, dragHandle)
        draggable.addStyleName(PRIVATE_CSS_DRAGGABLE)
        dragHandle.addStyleName(PRIVATE_CSS_HANDLE)
        dragHandles.put(draggable, dragHandle)
    
    
    """*
    * Performs the reverse of {@link #makeDraggable(Widget)}, detaching the
    * {@link MouseDragHandler} from the widget and removing any styling which was
    * applied when making the widget draggable.
    *
    * @param draggable the widget to no longer be draggable
    """
    def makeNotDraggable(self, draggable):
        Widget dragHandle = (Widget) dragHandles.remove(draggable)
        mouseDragHandler.makeNotDraggable(dragHandle)
        draggable.removeStyleName(PRIVATE_CSS_DRAGGABLE)
        dragHandle.removeStyleName(PRIVATE_CSS_HANDLE)
    
    
    def notifyDragEnd(self, dragEndEvent):
        raise UnsupportedOperationException()
    
    
    def previewDragEnd() throws VetoDragException {
        assert dragEndEvent is None
        if dragHandlers is not None:
            dragEndEvent = DragEndEvent(context)
            dragHandlers.firePreviewDragEnd(dragEndEvent)
        
    
    
    def previewDragEnd(Widget draggable, Widget dropTarget) throws VetoDragException {
        raise UnsupportedOperationException()
    
    
    def previewDragStart() throws VetoDragException {
        assert dragStartEvent is None
        if dragHandlers is not None:
            dragStartEvent = DragStartEvent(context)
            dragHandlers.firePreviewDragStart(dragStartEvent)
        
    
    
    def previewDragStart(Widget draggable) throws VetoDragException {
        raise UnsupportedOperationException()
    
    
    def removeDragHandler(self, handler):
        if dragHandlers is not None:
            dragHandlers.remove(handler)
        
    
    
    def resetCache(self):
    
    
    def setBehaviorConstrainedToBoundaryPanel(self, constrainedToBoundaryPanel):
        self.constrainedToBoundaryPanel = constrainedToBoundaryPanel
    
    
    def setBehaviorDragStartSensitivity(self, pixels):
        assert pixels >= 0
        dragStartPixels = pixels
    
    
    def setBehaviorMultipleSelection(self, multipleSelectionAllowed):
        self.multipleSelectionAllowed = multipleSelectionAllowed
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            widget.removeStyleName(CSS_SELECTED)
            iterator.remove()
        
    
    
    def setConstrainWidgetToBoundaryPanel(self, constrainWidgetToBoundaryPanel):
        setBehaviorConstrainedToBoundaryPanel(constrainWidgetToBoundaryPanel)
    
    
    def toggleSelection(self, draggable):
        assert draggable is not None
        if context.selectedWidgets.remove(draggable):
            draggable.removeStyleName(CSS_SELECTED)
         elif multipleSelectionAllowed:
            context.selectedWidgets.add(draggable)
            draggable.addStyleName(CSS_SELECTED)
         else:
            context.selectedWidgets.clear()
            context.selectedWidgets.add(draggable)
        
    
    
    """*
    * @deprecated Use {@link PickupDragController#newBoundaryDropController(AbsolutePanel, boolean)} instead.
    """
    def newBoundaryDropController(self):
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated Use {@link PickupDragController#newBoundaryDropController(AbsolutePanel, boolean)} instead.
    """
    BoundaryDropController newBoundaryDropController(AbsolutePanel boundaryPanel,
    boolean allowDropping) {
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated Use {@link PickupDragController#restoreSelectedWidgetsLocation()} instead.
    """
    def restoreDraggableLocation(self, draggable):
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated Use {@link PickupDragController#restoreSelectedWidgetsStyle()} instead.
    """
    def restoreDraggableStyle(self, draggable):
        raise UnsupportedOperationException()
    
    
    """*
    * @deprecated Use {@link PickupDragController#saveSelectedWidgetsLocationAndStyle()} instead.
    """
    def saveDraggableLocationAndStyle(self, draggable):
        raise UnsupportedOperationException()
    

