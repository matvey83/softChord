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
from pyjamas.ui.Widget import Widget

from pyjamas.dnd.util import DOMUtilImpl

"""*
* Provides DOM utility methods.
"""
class DOMUtil:
    
    impl = GWT.create(DOMUtilImpl.class)
    
    
    def cancelAllDocumentSelections(self):
        """*
        * Cancel all currently selected region(s) on the current page.
        """
        impl.cancelAllDocumentSelections()
    
    
    def fastSetElementPosition(self, elem, left, top):
        """*
        * Set an element's location as fast as possible, avoiding some of the overhead in
        * {@link com.google.gwt.user.client.ui.AbsolutePanel#setWidgetPosition(Widget, int, int)}.
        *
        * @param elem the element's whose position is to be modified
        * @param left the left pixel offset
        * @param top the top pixel offset
        """
        JS("""
        elem.style.left = left + "px";
        elem.style.top = top + "px";
        """)
    
    
    def findIntersect(self, parent, location, comparator):
        """*
        * TODO Handle LTR case once Bidi support is part of GWT.
        """
        widgetCount = parent.getWidgetCount()
        
        # short circuit in case dropTarget has no children
        if widgetCount == 0:
            return 0
        
        
        # binary search over range of widgets to find intersection
        low = 0
        high = widgetCount
        
        while True:
            mid = (low + high) / 2
            assert mid >= low
            assert mid < high
            midArea = WidgetArea(parent.getWidget(mid), None)
            if mid == low:
                if mid == 0:
                    if comparator.locationIndicatesIndexFollowingWidget(midArea, location):
                        return high
                     else:
                        return mid
                    
                 else:
                    return high
                
            
            if midArea.getBottom() < location.getTop():
                low = mid
             elif midArea.getTop() > location.getTop():
                high = mid
             elif midArea.getRight() < location.getLeft():
                low = mid
             elif midArea.getLeft() > location.getLeft():
                high = mid
             else:
                if comparator.locationIndicatesIndexFollowingWidget(midArea, location):
                    return mid + 1
                 else:
                    return mid
                
            
    
    def getBorderLeft(self, elem):
        """*
        * Gets an element's CSS based 'border-left-width' in pixels or <code>0</code>
        * (zero) when the element is hidden.
        *
        * @param elem the element to be measured
        * @return the width of the left CSS border in pixels
        """
        return impl.getBorderLeft(elem)
    
    
    def getBorderTop(self, elem):
        """*
        * Gets an element's CSS based 'border-top-widget' in pixels or <code>0</code>
        * (zero) when the element is hidden.
        *
        * @param elem the element to be measured
        * @return the width of the top CSS border in pixels
        """
        return impl.getBorderTop(elem)
    
    
    def getClientHeight(self, elem):
        """*
        * Gets an element's client height in pixels or <code>0</code> (zero) when
        * the element is hidden. This is equal to offset height minus the top and
        * bottom CSS borders.
        *
        * @param elem the element to be measured
        * @return the element's client height in pixels
        """
        return impl.getClientHeight(elem)
    
    
    def getClientWidth(self, elem):
        """*
        * Gets an element's client widget in pixels or <code>0</code> (zero) when
        * the element is hidden. This is equal to offset width minus the left and
        * right CSS borders.
        *
        * @param elem the element to be measured
        * @return the element's client width in pixels
        """
        return impl.getClientWidth(elem)
    
    
    def getHorizontalBorders(self, widget):
        """*
        * Gets the sum of an element's left and right CSS borders in pixels.
        *
        * @param widget the widget to be measured
        * @return the total border width in pixels
        """
        return impl.getHorizontalBorders(widget)
    
    
    def getNodeName(self, elem):
        """*
        * Determine an element's node name via the <code>nodeName</code> property.
        *
        * @param elem the element whose node name is to be determined
        * @return the element's node name
        """
        return impl.getNodeName(elem)
    
    
    def getVerticalBorders(self, widget):
        """*
        * Gets the sum of an element's top and bottom CSS borders in pixels.
        *
        * @param widget the widget to be measured
        * @return the total border height in pixels
        """
        return impl.getVerticalBorders(widget)
    
    
    def isOrContains(self, parent, child):
        """*
        * Determine if <code>parent</code> is an ancestor of <code>child</code>.
        *
        * TODO replace with DOM.isOrHasChild after GWT Issue 1218 is addressed
        *
        * @param parent the element to consider as the ancestor of <code>child</code>
        * @param child the element to consider as the descendant of <code>parent</code>
        * @return <code>True</code> if relationship holds
        """
        return impl.isOrContains(parent, child)
    
    
    def setStatus(self, text):
        """*
        * Set the browser's status bar text, if supported and enabled in the client browser.
        *
        * @param text the message to use as the window status
        """
        impl.setStatus(text)
    


