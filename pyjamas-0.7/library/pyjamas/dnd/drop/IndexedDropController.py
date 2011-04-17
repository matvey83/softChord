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



from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.IndexedPanel import IndexedPanel
from pyjamas.ui.Label import Label
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd.util import DOMUtil
from pyjamas.dnd.util import LocationWidgetComparator



"""*
* A {@link DropController} for instances of {@link IndexedPanel}.
*
* @see FlowPanelDropController
*
* TODO VerticalPanel performance is slow because of positioner DOM manipulation
"""
class IndexedDropController extends AbstractIndexedDropController:
    Label DUMMY_LABEL_IE_QUIRKS_MODE_OFFSET_HEIGHT = Label("x")
    
    IndexedPanel dropTarget
    
    def __init__(self, dropTarget):
        super(dropTarget)
        if not (dropTarget instanceof HorizontalPanel)  and  not (dropTarget instanceof VerticalPanel):
            raise IllegalArgumentException(GWT.getTypeName(dropTarget)
            + " is not currently supported by this controller")
        
        self.dropTarget = dropTarget
    
    
    def getLocationWidgetComparator(self):
        if dropTarget instanceof HorizontalPanel:
            return LocationWidgetComparator.RIGHT_HALF_COMPARATOR
         else:
            return LocationWidgetComparator.BOTTOM_HALF_COMPARATOR
        
    
    
    # TODO remove after enhancement for issue 1112 provides InsertPanel interface
    # http:#code.google.com/p/google-web-toolkit/issues/detail?id=1112
    def insert(self, widget, beforeIndex):
        if dropTarget instanceof HorizontalPanel:
            ((HorizontalPanel) dropTarget).insert(widget, beforeIndex)
         else:
            ((VerticalPanel) dropTarget).insert(widget, beforeIndex)
        
    
    
    def newPositioner(self, context):
        # Use two widgets so that setPixelSize() consistently affects dimensions
        # excluding positioner border in quirks and strict modes
        SimplePanel outer = SimplePanel()
        outer.addStyleName(CSS_DRAGDROP_POSITIONER)
        
        # place off screen for border calculation
        RootPanel.get().add(outer, -500, -500)
        
        # Ensure IE quirks mode returns valid outer.offsetHeight, and thus valid
        # DOMUtil.getVerticalBorders(outer)
        outer.setWidget(DUMMY_LABEL_IE_QUIRKS_MODE_OFFSET_HEIGHT)
        
        int width = 0
        int height = 0
        if dropTarget instanceof HorizontalPanel:
            for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
                Widget widget = (Widget) iterator.next()
                width += widget.getOffsetWidth()
                height = Math.max(height, widget.getOffsetHeight())
            
         else:
            for Iterator iterator = context.selectedWidgets.iterator(); iterator.hasNext();:
                Widget widget = (Widget) iterator.next()
                width = Math.max(width, widget.getOffsetWidth())
                height += widget.getOffsetHeight()
            
        
        
        SimplePanel inner = SimplePanel()
        inner.setPixelSize(width - DOMUtil.getHorizontalBorders(outer), height
        - DOMUtil.getVerticalBorders(outer))
        
        outer.setWidget(inner)
        
        return outer
    


