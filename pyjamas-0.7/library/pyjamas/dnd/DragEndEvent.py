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


from pyjamas.ui.Widget import Widget

from pyjamas.dnd.drop import DropController
from pyjamas.dnd.util import StringUtil

"""*
* {@link java.util.EventObject} containing information about the end of a drag.
"""
class DragEndEvent extends DragEvent:
    def __init__(self, context):
        super(context)
    
    
    """*
    * @deprecated Use {@link DragEvent#getContext() getContext()}.{@link DragContext#finalDropController finalDropController}.{@link DropController#getDropTarget() getDropTarget()} instead.
    """
    def getDropTarget(self):
        DropController finalDropController = context.finalDropController
        return finalDropController is None ? None : finalDropController.getDropTarget()
    
    
    """*
    * Return a string representation of this event.
    """
    def toString(self):
        String dropTargetText
        if context.finalDropController is not None:
            dropTargetText = "dropTarget="
            + StringUtil.getShortTypeName(context.finalDropController.getDropTarget())
         else:
            dropTargetText = "[cancelled]"
        
        return "DragEndEvent(" + dropTargetText + ", source=" + getSourceShortTypeName() + ")"
    


