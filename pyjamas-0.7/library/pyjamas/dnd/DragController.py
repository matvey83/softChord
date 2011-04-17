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
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.drop import DropController
from FiresDragEvents import FiresDragEvents

"""*
* Common interface which all drag controllers must implement.
"""
class DragController(FiresDragEvents):
    def addDragHandler(handler):
        """*
        * Register a drag handler which will listen for
        * {@link DragStartEvent DragStartEvents} and
        * and {@link DragEndEvent DragEndEvents}.
        *
        * @see #removeDragHandler(DragHandler)
        """
        
    def clearSelection():
        """*
        * All currently selected widgets are deselected.
        """
        
    def dragEnd():
        """*
        * Callback method for {@link MouseDragHandler}.
        """
        
    def dragEnd(draggable, dropTarget):
        """*
        * @deprecated Use {@link #dragEnd()} instead.
        """
        
    def dragMove():
        """*
        * Callback method for {@link MouseDragHandler}.
        """
        
    def dragStart():
        """*
        * Callback method for {@link MouseDragHandler} when a drag operation
        * is initiated for this drag controller.
        """
        
    def dragStart(draggable):
        """*
        * @deprecated Used {@link #dragStart()} instead.
        """
        
    def getBehaviorConstrainedToBoundaryPanel():
        """*
        * Determine whether or not drag operations are constrained to the boundary panel.
        *
        * @return <code>True</code> if drags are constrained to the boundary panel
        """
        
    def getBehaviorDragStartSensitivity():
        """*
        * Gets the number of pixels the mouse must be moved to initiate a drag operation.
        *
        * @return number of pixels or <code>0</code> (zero) if mouse down starts the drag
        """
        
    def getBehaviorMultipleSelection():
        """*
        * Determines whether multiple widget selection behavior is enabled.
        *
        * @return <code>True</code> if multiple widget selection behavior is enabled
        """
        
    def getBoundaryPanel():
        """*
        * Get the boundary panel provided in the constructor.
        *
        * @return the AbsolutePanel provided in the constructor
        """
        
    def getDropControllerCollection():
        """*
        * @deprecated No longer a part of the API.
        """
        
    def getIntersectDropController(widget):
        """*
        * @deprecated No longer a part of the API.
        """
        
    def getIntersectDropController(widget, x, y):
        """*
        * @deprecated No longer a part of the API.
        """
        
    def getMovableWidget():
        """*
        * @deprecated The movable panel is now returned by {@link #dragStart(Widget)}.
        """
        
    def makeDraggable(draggable):
        """*
        * Enable dragging on widget. Call this method for each widget that
        * you would like to make draggable under this drag controller.
        *
        * @param draggable the widget to be made draggable
        """
        
    def makeDraggable(draggable, dragHandle):
        """*
        * Enable dragging on widget, specifying the child widget serving as a
        * drag handle.
        *
        * @param draggable the widget to be made draggable
        * @param dragHandle the widget by which widget can be dragged
        """
        
    def makeNotDraggable(widget):
        """*
        * Performs the reverse of {@link #makeDraggable(Widget)}, making the widget
        * no longer draggable by this drag controller.
        *
        * @param widget the widget which should no longer be draggable
        """
        
    def notifyDragEnd(dragEndEvent):
        """*
        * @deprecated No longer a part of the API.
        """
        
    def previewDragEnd() throws VetoDragException
        """*
        * Callback method for {@link MouseDragHandler}.
        *
        * @throws VetoDragException if the proposed operation is unacceptable
        """
        
    def previewDragEnd(draggable, dropTarget) throws VetoDragException
        """*
        * @deprecated Used {@link #previewDragEnd()} instead.
        """
        
    def previewDragStart() throws VetoDragException
        """*
        * Callback method for {@link MouseDragHandler}.
        *
        * @throws VetoDragException if the proposed operation is unacceptable
        """
        
    def previewDragStart(draggable=None) throws VetoDragException
        """*
        * @deprecated Used {@link #previewDragStart()} instead.
        """
        
    def removeDragHandler(handler=None):
        """*
        * Unregister drag handler.
        *
        * @see #addDragHandler(DragHandler)
        """
        
    def resetCache():
        """*
        * Reset the internal drop controller (drop target) cache which is initialized by
        * {{@link #dragStart(Widget)}. This method should be called when a drop target's
        * size and/or location changes, or when drop target eligibility changes.
        """
        
    def setBehaviorConstrainedToBoundaryPanel(constrainedToBoundaryPanel=False):
        """*
        * Set whether or not movable widget is to be constrained to the boundary panel
        * during dragging. The default is not to constrain the draggable or drag proxy.
        *
        * @param constrainedToBoundaryPanel whether or not to constrain to the boundary panel
        """
        
        """*
        * Sets the number of pixels the mouse must be moved in either horizontal or vertical
        * direction in order to initiate a drag operation. Defaults to <code>0</code> (zero).
        * Use a value of at least <code>1</code> (one) in order to allow registered click
        * listeners to receive click events.
        *
        * @param pixels number of pixels or <code>0</code> (zero) to start dragging on mouse down
        """
    def setBehaviorDragStartSensitivity(pixels=0):
        
        """*
        * Sets whether multiple widgets can be selected for dragging at one time via
        * <code>CTRL</code>/<code>META</code>-click. Defaults to <code>True</code>.
        *
        * @param multipleSelectionAllowed whether multiple selections are enabled
        """
    def setBehaviorMultipleSelection(multipleSelectionAllowed):
        
        """*
        * @deprecated Use {@link #setBehaviorConstrainedToBoundaryPanel(boolean)} instead.
        """
    def setConstrainWidgetToBoundaryPanel(constrainWidgetToBoundaryPanel):
        
        """*
        * Toggle the selection of the specified widget.
        *
        * @param draggable the widget whose selection is to be toggled
        """
    def toggleSelection(draggable):

