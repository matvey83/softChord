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


from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd.util import LocationWidgetComparator

"""*
* A {@link DropController} for instances of {@link FlowPanel}.
*
* @see IndexedDropController
"""
class FlowPanelDropController(AbstractIndexedDropController):
    CSS_DRAGDROP_FLOW_PANEL_POSITIONER = "dragdrop-flow-panel-positioner"
    
    """*
    * @see IndexedDropController#IndexedDropController(com.google.gwt.user.client.ui.IndexedPanel)
    *
    * @param dropTarget
    """
    def __init__(self, dropTarget):
        super(dropTarget)
        self.dropTarget = dropTarget
    
    
    def getLocationWidgetComparator(self):
        return LocationWidgetComparator.BOTTOM_RIGHT_COMPARATOR
    
    
    # TODO remove after enhancement for issue 1112 provides InsertPanel interface
    # http:#code.google.com/p/google-web-toolkit/issues/detail?id=1112
    def insert(self, widget, beforeIndex):
        dropTarget.insert(widget, beforeIndex)
    
    
    def newPositioner(self, context):
        positioner = HTML("&#x203B;")
        positioner.addStyleName(CSS_DRAGDROP_FLOW_PANEL_POSITIONER)
        return positioner
    


