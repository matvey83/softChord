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


from pyjamas.ui.IndexedPanel import IndexedPanel
from pyjamas.ui.Panel import Panel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd import VetoDragException
from pyjamas.dnd.util import CoordinateLocation
from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import LocationWidgetComparator



"""*
* A {@link DropController} for {@link IndexedPanel} drop targets.
"""
abstract class AbstractIndexedDropController extends AbstractPositioningDropController:
    int dropIndex
    IndexedPanel dropTarget
    Widget positioner = None
    
    """*
    * @see FlowPanelDropController#FlowPanelDropController(com.google.gwt.user.client.ui.FlowPanel)
    *
    * @param dropTarget
    """
    def __init__(self, dropTarget):
        super((Panel) dropTarget)
        self.dropTarget = dropTarget
    
    
    def onDrop(self, context):
        assert dropIndex != -1 : "Should not happen after onPreviewDrop did not veto"
        for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
            Widget widget = (Widget) iterator.next()
            insert(widget, dropIndex++)
        
        super.onDrop(context)
    
    
    def onEnter(self, context):
        super.onEnter(context)
        positioner = newPositioner(context)
    
    
    def onLeave(self, context):
        positioner.removeFromParent()
        positioner = None
        super.onLeave(context)
    
    
    def onMove(self, context):
        super.onMove(context)
        int targetIndex = DOMUtil.findIntersect(dropTarget, CoordinateLocation(context.mouseX,
        context.mouseY), getLocationWidgetComparator())
        
        # check that positioner not already in the correct location
        int positionerIndex = dropTarget.getWidgetIndex(positioner)
        
        if positionerIndex != targetIndex  and  (positionerIndex != targetIndex - 1  or  targetIndex == 0):
            if positionerIndex == 0  and  dropTarget.getWidgetCount() == 1:
                # do nothing, the positioner is the only widget
             elif targetIndex == -1:
                # outside drop target, so remove positioner to indicate a drop will not happen
                positioner.removeFromParent()
             else:
                insert(positioner, targetIndex)
            
        
    
    
    void onPreviewDrop(DragContext context) throws VetoDragException {
        dropIndex = dropTarget.getWidgetIndex(positioner)
        if dropIndex == -1:
            raise VetoDragException()
        
        super.onPreviewDrop(context)
    
    
    abstract LocationWidgetComparator getLocationWidgetComparator()
    
    """*
    * Insert the provided widget using an appropriate drop target specific method.
    *
    * TODO remove after enhancement for issue 1112 provides InsertPanel interface
    *
    * @param widget the widget to be inserted
    * @param beforeIndex the widget index before which <code>widget</code> should be inserted
    """
    abstract void insert(Widget widget, int beforeIndex)
    
    """*
    * Called by {@link AbstractIndexedDropController#onEnter(DragContext)} to create a new
    * positioner widget for this indexed drop target. Override this method to customize
    * the look and feel of your positioner. The positioner widget may not have any CSS
    * borders or margins, although there are no such restrictions on the children of the
    * positioner widget. If borders and/or margins are desired, wrap that widget in a
    * {@link SimplePanel} with a <code>0px</code> border and margin.
    *
    * @param context The current drag context.
    * @return a positioner widget
    """
    abstract Widget newPositioner(DragContext context)


