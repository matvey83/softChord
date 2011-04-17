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
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.drop import BoundaryDropController
from pyjamas.dnd.drop import DropController
from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import Location
from pyjamas.dnd.util import WidgetArea
from pyjamas.dnd.util import WidgetLocation





"""*
* DragController used for drag-and-drop operations where a draggable widget or
* drag proxy is temporarily picked up and dragged around the boundary panel.
* Be sure to register a {@link DropController} for each drop target.
*
* @see #registerDropController(DropController)
"""
class PickupDragController extends AbstractDragController:
    class SavedWidgetInfo:
        int initialDraggableIndex
        String initialDraggableMargin
        Widget initialDraggableParent
        Location initialDraggableParentLocation
    
    
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    String CSS_MOVABLE_PANEL
    
    """*
    * @deprecated Instead selectively use your own CSS classes.
    """
    String CSS_PROXY
    String PRIVATE_CSS_MOVABLE_PANEL = "dragdrop-movable-panel"
    String PRIVATE_CSS_PROXY = "dragdrop-proxy"
    
    {
        CSS_MOVABLE_PANEL = PRIVATE_CSS_MOVABLE_PANEL
        CSS_PROXY = PRIVATE_CSS_PROXY
    
    
    BoundaryDropController boundaryDropController
    int boundaryOffsetX
    int boundaryOffsetY
    boolean dragProxyEnabled = False
    DropControllerCollection dropControllerCollection
    ArrayList dropControllerList = ArrayList()
    int dropTargetClientHeight
    int dropTargetClientWidth
    Widget movablePanel
    HashMap savedWidgetInfoMap
    
    """*
    * Create a pickup-and-move style drag controller. Allows widgets or a
    * suitable proxy to be temporarily picked up and moved around the specified
    * boundary panel.
    *
    * <p>
    * Note: An implicit {@link BoundaryDropController} is created and registered
    * automatically.
    * </p>
    *
    * @param boundaryPanel the desired boundary panel or <code>RootPanel.get()</code>
    *                      if entire document body is to be the boundary
    * @param allowDroppingOnBoundaryPanel whether or not boundary panel should
    *            allow dropping
    """
    def __init__(self, boundaryPanel, allowDroppingOnBoundaryPanel):
        super(boundaryPanel)
        assert boundaryPanel is not None : "Use 'RootPanel.get()' instead of 'None'."
        boundaryDropController = newBoundaryDropController(boundaryPanel, allowDroppingOnBoundaryPanel)
        registerDropController(boundaryDropController)
        dropControllerCollection = DropControllerCollection(dropControllerList)
    
    
    def dragEnd(self):
        assert context.finalDropController is None == (context.vetoException is not None)
        if context.vetoException is not None:
            if not getBehaviorDragProxy():
                restoreSelectedWidgetsLocation()
            
         else:
            context.dropController.onDrop(context)
        
        context.dropController.onLeave(context)
        context.dropController = None
        
        if not getBehaviorDragProxy():
            restoreSelectedWidgetsStyle()
        
        movablePanel.removeFromParent()
        movablePanel = None
        super.dragEnd()
    
    
    def dragMove(self):
        int desiredLeft = context.desiredDraggableX - boundaryOffsetX
        int desiredTop = context.desiredDraggableY - boundaryOffsetY
        if getBehaviorConstrainedToBoundaryPanel():
            desiredLeft = Math.max(0, Math.min(desiredLeft, dropTargetClientWidth
            - context.draggable.getOffsetWidth()))
            desiredTop = Math.max(0, Math.min(desiredTop, dropTargetClientHeight
            - context.draggable.getOffsetHeight()))
        
        
        DOMUtil.fastSetElementPosition(movablePanel.getElement(), desiredLeft, desiredTop)
        
        DropController newDropController = getIntersectDropController(context.mouseX, context.mouseY)
        if context.dropController != newDropController:
            if context.dropController is not None:
                context.dropController.onLeave(context)
            
            context.dropController = newDropController
            if context.dropController is not None:
                context.dropController.onEnter(context)
            
        
        
        if context.dropController is not None:
            context.dropController.onMove(context)
        
    
    
    def dragStart(self):
        super.dragStart()
        
        WidgetLocation currentDraggableLocation = WidgetLocation(context.draggable,
        context.boundaryPanel)
        if getBehaviorDragProxy():
            movablePanel = newDragProxy(context)
            context.boundaryPanel.add(movablePanel, currentDraggableLocation.getLeft(),
            currentDraggableLocation.getTop())
         else:
            saveSelectedWidgetsLocationAndStyle()
            AbsolutePanel container = AbsolutePanel()
            DOM.setStyleAttribute(container.getElement(), "overflow", "visible")
            
            container.setPixelSize(context.draggable.getOffsetWidth(),
            context.draggable.getOffsetHeight())
            context.boundaryPanel.add(container, currentDraggableLocation.getLeft(),
            currentDraggableLocation.getTop())
            
            int draggableAbsoluteLeft = context.draggable.getAbsoluteLeft()
            int draggableAbsoluteTop = context.draggable.getAbsoluteTop()
            for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
                Widget widget = (Widget) iterator.next()
                if widget != context.draggable:
                    int relativeX = widget.getAbsoluteLeft() - draggableAbsoluteLeft
                    int relativeY = widget.getAbsoluteTop() - draggableAbsoluteTop
                    container.add(widget, relativeX, relativeY)
                
            
            container.add(context.draggable, 0, 0)
            movablePanel = container
        
        movablePanel.addStyleName(PRIVATE_CSS_MOVABLE_PANEL)
        
        # one time calculation of boundary panel location for efficiency during dragging
        Location widgetLocation = WidgetLocation(context.boundaryPanel, None)
        boundaryOffsetX = widgetLocation.getLeft()
        + DOMUtil.getBorderLeft(context.boundaryPanel.getElement())
        boundaryOffsetY = widgetLocation.getTop()
        + DOMUtil.getBorderTop(context.boundaryPanel.getElement())
        
        dropTargetClientWidth = DOMUtil.getClientWidth(boundaryPanel.getElement())
        dropTargetClientHeight = DOMUtil.getClientHeight(boundaryPanel.getElement())
    
    
    """*
    * Whether or not dropping on the boundary panel is permitted.
    *
    * @return <code>True</code> if dropping on the boundary panel is allowed
    """
    def getBehaviorBoundaryPanelDrop(self):
        return boundaryDropController.getBehaviorBoundaryPanelDrop()
    
    
    """*
    * Determine whether or not this controller automatically creates a drag proxy
    * for each drag operation. Whether or not a drag proxy is used is ultimately
    * determined by the return value of {@link #maybeNewDraggableProxy(Widget)}
    *
    * @return <code>True</code> if drag proxy behavior is enabled
    """
    def getBehaviorDragProxy(self):
        return dragProxyEnabled
    
    
    """*
    * @deprecated Use {@link #getBehaviorDragProxy()} instead.
    """
    def isDragProxyEnabled(self):
        return getBehaviorDragProxy()
    
    
    void previewDragEnd() throws VetoDragException {
        assert context.finalDropController is None
        assert context.vetoException is None
        # Does the DropController allow the drop?
        try:
            context.dropController.onPreviewDrop(context)
            context.finalDropController = context.dropController
        except ex:
            context.finalDropController = None
            raise ex
         finally {
            super.previewDragEnd()
        
    
    
    """*
    * Register a DropController, representing a drop target, with this
    * drag controller.
    *
    * @see #unregisterDropController(DropController)
    *
    * @param dropController the controller to register
    """
    def registerDropController(self, dropController):
        dropControllerList.add(dropController)
    
    
    def resetCache(self):
        super.resetCache()
        dropControllerCollection.resetCache(boundaryPanel, context)
    
    
    """*
    * Set whether or not widgets may be dropped anywhere on the boundary panel.
    * Set to <code>False</code> when you only want explicitly registered drop
    * controllers to accept drops. Defaults to <code>True</code>.
    *
    * @param allowDroppingOnBoundaryPanel <code>True</code> to allow dropping
    """
    def setBehaviorBoundaryPanelDrop(self, allowDroppingOnBoundaryPanel):
        boundaryDropController.setBehaviorBoundaryPanelDrop(allowDroppingOnBoundaryPanel)
    
    
    """*
    * Set whether or not this controller should automatically create a drag proxy
    * for each drag operation. Whether or not a drag proxy is used is ultimately
    * determined by the return value of {@link #maybeNewDraggableProxy(Widget)}.
    *
    * @param dragProxyEnabled <code>True</code> to enable drag proxy behavior
    """
    def setBehaviorDragProxy(self, dragProxyEnabled):
        self.dragProxyEnabled = dragProxyEnabled
    
    
    """*
    * @deprecated Use {@link #setBehaviorDragProxy(boolean)} instead.
    """
    def setDragProxyEnabled(self, dragProxyEnabled):
        setBehaviorDragProxy(dragProxyEnabled)
    
    
    """*
    * Unregister a DropController from this drag controller.
    *
    * @see #registerDropController(DropController)
    *
    * @param dropController the controller to register
    """
    def unregisterDropController(self, dropController):
        dropControllerList.remove(dropController)
    
    
    """*
    * @deprecated Use {@link #newDragProxy(DragContext)} and {@link #setBehaviorDragProxy(boolean)} instead.
    """
    def maybeNewDraggableProxy(self, draggable):
        raise UnsupportedOperationException()
    
    
    """*
    * Create a BoundaryDropController to manage our boundary panel as a drop
    * target. To ensure that draggable widgets can only be dropped on registered
    * drop targets, set <code>allowDroppingOnBoundaryPanel</code> to <code>False</code>.
    *
    * @param boundaryPanel the panel to which our drag-and-drop operations are constrained
    * @param allowDroppingOnBoundaryPanel whether or not dropping is allowed on the boundary panel
    * @return the BoundaryDropController
    """
    BoundaryDropController newBoundaryDropController(AbsolutePanel boundaryPanel,
    boolean allowDroppingOnBoundaryPanel) {
        return BoundaryDropController(boundaryPanel, allowDroppingOnBoundaryPanel)
    
    
    """*
    * Called by {@link PickupDragController#dragStart(Widget)} to allow subclasses to
    * provide their own drag proxies.
    *
    * @param context the current drag context
    * @return a drag proxy
    """
    def newDragProxy(self, context):
        AbsolutePanel container = AbsolutePanel()
        DOM.setStyleAttribute(container.getElement(), "overflow", "visible")
        
        WidgetArea draggableArea = WidgetArea(context.draggable, None)
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            WidgetArea widgetArea = WidgetArea(widget, None)
            Widget proxy = SimplePanel()
            proxy.setPixelSize(widget.getOffsetWidth(), widget.getOffsetHeight())
            proxy.addStyleName(PRIVATE_CSS_PROXY)
            container.add(proxy, widgetArea.getLeft() - draggableArea.getLeft(), widgetArea.getTop()
            - draggableArea.getTop())
        
        
        return container
    
    
    """*
    * Restore the selected widgets to their original location.
    * @see #saveSelectedWidgetsLocationAndStyle()
    * @see #restoreSelectedWidgetsStyle()
    """
    def restoreSelectedWidgetsLocation(self):
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            SavedWidgetInfo info = (SavedWidgetInfo) savedWidgetInfoMap.get(widget)
            
            # TODO simplify after enhancement for issue 1112 provides InsertPanel interface
            # http:#code.google.com/p/google-web-toolkit/issues/detail?id=1112
            if info.initialDraggableParent instanceof AbsolutePanel:
                ((AbsolutePanel) info.initialDraggableParent).add(widget,
                info.initialDraggableParentLocation.getLeft(),
                info.initialDraggableParentLocation.getTop())
             elif info.initialDraggableParent instanceof HorizontalPanel:
                ((HorizontalPanel) info.initialDraggableParent).insert(widget, info.initialDraggableIndex)
             elif info.initialDraggableParent instanceof VerticalPanel:
                ((VerticalPanel) info.initialDraggableParent).insert(widget, info.initialDraggableIndex)
             elif info.initialDraggableParent instanceof FlowPanel:
                ((FlowPanel) info.initialDraggableParent).insert(widget, info.initialDraggableIndex)
             elif info.initialDraggableParent instanceof SimplePanel:
                ((SimplePanel) info.initialDraggableParent).setWidget(widget)
             else:
                raise RuntimeException("Unable to handle initialDraggableParent "
                + GWT.getTypeName(info.initialDraggableParent))
            
        
    
    
    """*
    * Restore the selected widgets with their original style.
    * @see #saveSelectedWidgetsLocationAndStyle()
    * @see #restoreSelectedWidgetsLocation()
    """
    def restoreSelectedWidgetsStyle(self):
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            SavedWidgetInfo info = (SavedWidgetInfo) savedWidgetInfoMap.get(widget)
            DOM.setStyleAttribute(widget.getElement(), "margin", info.initialDraggableMargin)
        
    
    
    """*
    * Save the selected widgets' current location in case they much
    * be restored due to a canceled drop.
    * @see #restoreSelectedWidgetsLocation()
    """
    def saveSelectedWidgetsLocationAndStyle(self):
        savedWidgetInfoMap = HashMap()
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            
            SavedWidgetInfo info = SavedWidgetInfo()
            info.initialDraggableParent = widget.getParent()
            
            # TODO simplify after enhancement for issue 1112 provides InsertPanel interface
            # http:#code.google.com/p/google-web-toolkit/issues/detail?id=1112
            if info.initialDraggableParent instanceof AbsolutePanel:
                info.initialDraggableParentLocation = WidgetLocation(widget,
                info.initialDraggableParent)
             elif info.initialDraggableParent instanceof HorizontalPanel:
                info.initialDraggableIndex = ((HorizontalPanel) info.initialDraggableParent).getWidgetIndex(widget)
             elif info.initialDraggableParent instanceof VerticalPanel:
                info.initialDraggableIndex = ((VerticalPanel) info.initialDraggableParent).getWidgetIndex(widget)
             elif info.initialDraggableParent instanceof FlowPanel:
                info.initialDraggableIndex = ((FlowPanel) info.initialDraggableParent).getWidgetIndex(widget)
             elif info.initialDraggableParent instanceof SimplePanel:
                # save nothing
             else:
                raise RuntimeException(
                "Unable to handle 'initialDraggableParent instanceof "
                + GWT.getTypeName(info.initialDraggableParent)
                + "'; Please create your own DragController and override saveDraggableLocationAndStyle() and restoreDraggableLocation()")
            
            
            info.initialDraggableMargin = DOM.getStyleAttribute(widget.getElement(), "margin")
            DOM.setStyleAttribute(widget.getElement(), "margin", "0px")
            savedWidgetInfoMap.put(widget, info)
        
    
    
    def getIntersectDropController(self, x, y):
        DropController dropController = dropControllerCollection.getIntersectDropController(x, y)
        return dropController is not None ? dropController : boundaryDropController
    


