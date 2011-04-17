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
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Widget import Widget

from pyjamas.dnd import DragContext
from pyjamas.dnd import VetoDragException

"""*
* A {@link DropController} for the {@link com.google.gwt.user.client.ui.Panel}
* which contains a given draggable widget.
"""
class BoundaryDropController extends AbsolutePositionDropController:
    boolean allowDroppingOnBoundaryPanel = True
    
    def __init__(self, dropTarget, allowDroppingOnBoundaryPanel):
        super(dropTarget)
        dropTarget.addStyleName("dragdrop-boundary")
        self.allowDroppingOnBoundaryPanel = allowDroppingOnBoundaryPanel
    
    
    """*
    * Whether or not dropping on the boundary panel is permitted.
    *
    * @return <code>True</code> if dropping on the boundary panel is allowed
    """
    def getBehaviorBoundaryPanelDrop(self):
        return allowDroppingOnBoundaryPanel
    
    
    void onPreviewDrop(DragContext context) throws VetoDragException {
        if not allowDroppingOnBoundaryPanel:
            raise VetoDragException()
        
        super.onPreviewDrop(context)
    
    
    """*
    * Set whether or not widgets may be dropped anywhere on the boundary panel.
    * Set to <code>False</code> when you only want explicitly registered drop
    * controllers to accept drops. Defaults to <code>True</code>.
    *
    * @param allowDroppingOnBoundaryPanel <code>True</code> to allow dropping
    """
    def setBehaviorBoundaryPanelDrop(self, allowDroppingOnBoundaryPanel):
        self.allowDroppingOnBoundaryPanel = allowDroppingOnBoundaryPanel
    
    
    def makePositioner(self, reference):
        if allowDroppingOnBoundaryPanel:
            return super.makePositioner(reference)
         else:
            return SimplePanel()
        
    


