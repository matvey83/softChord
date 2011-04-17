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
from pyjamas.ui.AbsolutePanel import AbsolutePanel
from pyjamas.ui.Label import Label
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import Location
from pyjamas.dnd.util import WidgetLocation




"""*
* A {@link DropController} which allows a draggable widget to be placed at
* specific (absolute) locations on an
* {@link com.google.gwt.user.client.ui.AbsolutePanel} drop target.
"""
class AbsolutePositionDropController extends AbstractPositioningDropController:
    class Draggable:
        int desiredX
        int desiredY
        int relativeX
        int relativeY
        int offsetHeight
        int offsetWidth
        Widget positioner = None
        Widget widget
        
        def __init__(self, widget):
            self.widget = widget
            offsetWidth = widget.getOffsetWidth()
            offsetHeight = widget.getOffsetHeight()
        
    
    
    Label DUMMY_LABEL_IE_QUIRKS_MODE_OFFSET_HEIGHT = Label("x")
    ArrayList draggableList = ArrayList()
    AbsolutePanel dropTarget
    int dropTargetClientHeight
    int dropTargetClientWidth
    int dropTargetOffsetX
    int dropTargetOffsetY
    
    def __init__(self, dropTarget):
        super(dropTarget)
        self.dropTarget = dropTarget
    
    
    """*
    * Programmatically drop a widget on our drop target while obeying the
    * constraints of this controller.
    *
    * @param widget the widget to be dropped
    * @param left the desired absolute horizontal location relative to our drop
    *            target
    * @param top the desired absolute vertical location relative to our drop
    *            target
    """
    def drop(self, widget, left, top):
        left = Math.max(0, Math.min(left, dropTarget.getOffsetWidth() - widget.getOffsetWidth()))
        top = Math.max(0, Math.min(top, dropTarget.getOffsetHeight() - widget.getOffsetHeight()))
        dropTarget.add(widget, left, top)
    
    
    def onDrop(self, context):
        for Iterator iterator = draggableList.iterator(); iterator.hasNext();:
            Draggable draggable = (Draggable) iterator.next()
            draggable.positioner.removeFromParent()
            dropTarget.add(draggable.widget, draggable.desiredX, draggable.desiredY)
        
        super.onDrop(context)
    
    
    def onEnter(self, context):
        super.onEnter(context)
        assert draggableList.size() == 0
        
        dropTargetClientWidth = DOMUtil.getClientWidth(dropTarget.getElement())
        dropTargetClientHeight = DOMUtil.getClientHeight(dropTarget.getElement())
        WidgetLocation dropTargetLocation = WidgetLocation(dropTarget, None)
        dropTargetOffsetX = dropTargetLocation.getLeft()
        + DOMUtil.getBorderLeft(dropTarget.getElement())
        dropTargetOffsetY = dropTargetLocation.getTop() + DOMUtil.getBorderTop(dropTarget.getElement())
        
        int draggableAbsoluteLeft = context.draggable.getAbsoluteLeft()
        int draggableAbsoluteTop = context.draggable.getAbsoluteTop()
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            Draggable draggable = Draggable(widget)
            draggable.positioner = makePositioner(widget)
            draggable.relativeX = widget.getAbsoluteLeft() - draggableAbsoluteLeft
            draggable.relativeY = widget.getAbsoluteTop() - draggableAbsoluteTop
            draggableList.add(draggable)
        
    
    
    def onLeave(self, context):
        for Iterator iterator = draggableList.iterator(); iterator.hasNext();:
            Draggable draggable = (Draggable) iterator.next()
            draggable.positioner.removeFromParent()
        
        draggableList.clear()
        super.onLeave(context)
    
    
    def onMove(self, context):
        super.onMove(context)
        for Iterator iterator = draggableList.iterator(); iterator.hasNext();:
            Draggable draggable = (Draggable) iterator.next()
            draggable.desiredX = context.desiredDraggableX - dropTargetOffsetX + draggable.relativeX
            draggable.desiredY = context.desiredDraggableY - dropTargetOffsetY + draggable.relativeY
            draggable.desiredX = Math.max(0, Math.min(draggable.desiredX, dropTargetClientWidth
            - draggable.offsetWidth))
            draggable.desiredY = Math.max(0, Math.min(draggable.desiredY, dropTargetClientHeight
            - draggable.offsetHeight))
            dropTarget.add(draggable.positioner, draggable.desiredX, draggable.desiredY)
        
    
    
    """*
    * @deprecated No longer a part of the API.
    """
    def getConstrainedLocation(self, reference, draggable, widget):
        raise UnsupportedOperationException()
    
    
    def makePositioner(self, reference):
        # Use two widgets so that setPixelSize() consistently affects dimensions
        # excluding positioner border in quirks and strict modes
        SimplePanel outer = SimplePanel()
        outer.addStyleName(CSS_DRAGDROP_POSITIONER)
        DOM.setStyleAttribute(outer.getElement(), "margin", "0px")
        
        # place off screen for border calculation
        RootPanel.get().add(outer, -500, -500)
        
        # Ensure IE quirks mode returns valid outer.offsetHeight, and thus valid
        # DOMUtil.getVerticalBorders(outer)
        outer.setWidget(DUMMY_LABEL_IE_QUIRKS_MODE_OFFSET_HEIGHT)
        
        SimplePanel inner = SimplePanel()
        DOM.setStyleAttribute(inner.getElement(), "margin", "0px")
        DOM.setStyleAttribute(inner.getElement(), "border", "none")
        int offsetWidth = reference.getOffsetWidth() - DOMUtil.getHorizontalBorders(outer)
        int offsetHeight = reference.getOffsetHeight() - DOMUtil.getVerticalBorders(outer)
        inner.setPixelSize(offsetWidth, offsetHeight)
        
        outer.setWidget(inner)
        
        return outer
    


