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


from pyjamas import Command
from pyjamas import DOM
from pyjamas import DeferredCommand
from pyjamas import Event
from pyjamas.ui.FocusPanel import FocusPanel
from pyjamas.ui.MouseListener import MouseListener
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SourcesMouseEvents import SourcesMouseEvents
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import Location
from pyjamas.dnd.util import WidgetLocation



"""*
* Implementation helper class which handles mouse events for all
* draggable widgets for a given {@link DragController}.
"""
class MouseDragHandler implements MouseListener:
    int ACTIVELY_DRAGGING = 3
    int DRAGGING_NO_MOVEMENT_YET = 2
    int NOT_DRAGGING = 1
    
    FocusPanel capturingWidget
    DragContext context
    DeferredMoveCommand deferredMoveCommand = DeferredMoveCommand(this)
    int dragging = NOT_DRAGGING
    HashMap dragHandleMap = HashMap()
    boolean mouseDown
    int mouseDownOffsetX
    int mouseDownOffsetY
    Widget mouseDownWidget
    
    def __init__(self, context):
        self.context = context
        initCapturingWidget()
    
    
    def onMouseDown(self, sender, x, y):
        if dragging == ACTIVELY_DRAGGING  or  dragging == DRAGGING_NO_MOVEMENT_YET:
            # Ignore additional mouse buttons depressed while still dragging
            return
        
        
        Event event = DOM.eventGetCurrentEvent()
        int button = DOM.eventGetButton(event)
        # TODO remove Event.UNDEFINED after GWT Issue 1535 is fixed
        if button != Event.BUTTON_LEFT  and  button != Event.UNDEFINED:
            return
        
        
        # mouse down (not first mouse move) determines draggable widget
        mouseDownWidget = sender
        context.draggable = (Widget) dragHandleMap.get(mouseDownWidget)
        assert context.draggable is not None
        
        if not toggleKey(event)  and  not context.selectedWidgets.contains(mouseDownWidget):
            context.dragController.clearSelection()
            context.dragController.toggleSelection(context.draggable)
        
        DeferredCommand.addCommand(Command() {
            def execute(self):
                DOMUtil.cancelAllDocumentSelections()
            
        )
        
        mouseDown = True
        DOM.eventPreventDefault(event)
        
        mouseDownOffsetX = x
        mouseDownOffsetY = y
        WidgetLocation loc1 = WidgetLocation(mouseDownWidget, None)
        if mouseDownWidget != context.draggable:
            WidgetLocation loc2 = WidgetLocation(context.draggable, None)
            mouseDownOffsetX += loc1.getLeft() - loc2.getLeft()
            mouseDownOffsetY += loc1.getTop() - loc2.getTop()
        
        if context.dragController.getBehaviorDragStartSensitivity() == 0  and  not toggleKey(event):
            startDragging()
            actualMove(x + loc1.getLeft(), y + loc1.getTop())
        
    
    
    def onMouseEnter(self, sender):
    
    
    def onMouseLeave(self, sender):
    
    
    def onMouseMove(self, sender, x, y):
        if dragging == ACTIVELY_DRAGGING  or  dragging == DRAGGING_NO_MOVEMENT_YET:
            # TODO remove Safari workaround after GWT issue 1807 fixed
            if sender != capturingWidget:
                # In Safari 1.3.2 MAC, other mouse events continue to arrive even when capturing
                return
            
            dragging = ACTIVELY_DRAGGING
         else:
            if mouseDown:
                if Math.max(Math.abs(x - mouseDownOffsetX), Math.abs(y - mouseDownOffsetY)) >= context.dragController.getBehaviorDragStartSensitivity():
                    DOMUtil.cancelAllDocumentSelections()
                    if not context.selectedWidgets.contains(context.draggable):
                        context.dragController.toggleSelection(context.draggable)
                    
                    startDragging()
                    
                    # adjust (x,y) to be relative to capturingWidget at (0,0)
                    Location location = WidgetLocation(mouseDownWidget, None)
                    x += location.getLeft()
                    y += location.getTop()
                
            
            if dragging == NOT_DRAGGING:
                return
            
        
        # proceed with the actual drag
        DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
        #    try:
            deferredMoveCommand.scheduleOrExecute(x, y)
            #    except ex:
                #      cancelDrag()
                #      raise ex
                #    }
            
            
            def onMouseUp(self, sender, x, y):
                Event event = DOM.eventGetCurrentEvent()
                int button = DOM.eventGetButton(event)
                # TODO Remove Event.UNDEFINED after GWT Issue 1535 is fixed
                if button != Event.BUTTON_LEFT  and  button != Event.UNDEFINED:
                    return
                
                mouseDown = False
                
                # in case mouse down occurred elsewhere
                if mouseDownWidget is None:
                    return
                
                
                if dragging != ACTIVELY_DRAGGING:
                    Widget widget = (Widget) dragHandleMap.get(mouseDownWidget)
                    assert widget is not None
                    if not toggleKey(event):
                        context.dragController.clearSelection()
                    
                    context.dragController.toggleSelection(widget)
                    DOMUtil.cancelAllDocumentSelections()
                    if dragging == NOT_DRAGGING:
                        return
                    
                
                # TODO Remove Safari workaround after GWT issue 1807 fixed
                if sender != capturingWidget:
                    # In Safari 1.3.2 MAC does not honor capturing widget for mouse up
                    Location location = WidgetLocation(sender, None)
                    x += location.getLeft()
                    y += location.getTop()
                
                # Proceed with the drop
                try:
                    drop(x, y)
                 finally {
                    dragEndCleanup()
                
            
            
            def actualMove(self, x, y):
                context.mouseX = x
                context.mouseY = y
                context.desiredDraggableX = x - mouseDownOffsetX
                context.desiredDraggableY = y - mouseDownOffsetY
                
                context.dragController.dragMove()
            
            
            def makeDraggable(self, draggable, dragHandle):
                if dragHandle instanceof SourcesMouseEvents:
                    ((SourcesMouseEvents) dragHandle).addMouseListener(this)
                    dragHandleMap.put(dragHandle, draggable)
                 else:
                    raise RuntimeException("dragHandle must implement SourcesMouseEvents to be draggable")
                
            
            
            def makeNotDraggable(self, dragHandle):
                if dragHandleMap.remove(dragHandle) is None:
                    raise RuntimeException("dragHandle was not draggable")
                
                ((SourcesMouseEvents) dragHandle).removeMouseListener(this)
            
            
            def dragEndCleanup(self):
                DOM.releaseCapture(capturingWidget.getElement())
                dragging = NOT_DRAGGING
                context.dragEndCleanup()
            
            
            def drop(self, x, y):
                actualMove(x, y)
                dragging = NOT_DRAGGING
                
                # Does the DragController allow the drop?
                try:
                    context.dragController.previewDragEnd()
                except ex:
                    context.vetoException = ex
                
                
                context.dragController.dragEnd()
            
            
            def initCapturingWidget(self):
                capturingWidget = FocusPanel()
                capturingWidget.setPixelSize(0, 0)
                RootPanel.get().add(capturingWidget, 0, 0)
                capturingWidget.addMouseListener(this)
                DOM.setStyleAttribute(capturingWidget.getElement(), "visibility", "hidden")
                DOM.setStyleAttribute(capturingWidget.getElement(), "margin", "0px")
                DOM.setStyleAttribute(capturingWidget.getElement(), "border", "none")
            
            
            def startDragging(self):
                context.dragStartCleanup()
                try:
                    context.dragController.previewDragStart()
                except ex:
                    context.vetoException = ex
                    return
                
                context.dragController.dragStart()
                
                DOM.setCapture(capturingWidget.getElement())
                dragging = DRAGGING_NO_MOVEMENT_YET
            
            
            def toggleKey(self, event):
                return DOM.eventGetCtrlKey(event)  or  DOM.eventGetMetaKey(event)
            
        
        
