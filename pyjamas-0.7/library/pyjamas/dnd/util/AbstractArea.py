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


"""*
* Provides implementations for common {@link Area} calculations.
"""
abstract class AbstractArea implements Area:
    int bottom
    int left
    int right
    int top
    
    def copyOf(self):
        return CoordinateArea(getLeft(), getTop(), getRight(), getBottom())
    
    
    def distanceToEdge(self, location):
        int xDistance = Math.max(left - location.getLeft(), location.getLeft() - right)
        int yDistance = Math.max(top - location.getTop(), location.getTop() - bottom)
        return Math.max(xDistance, yDistance)
    
    
    def getBottom(self):
        return bottom
    
    
    def getCenter(self):
        return CoordinateLocation(left + getWidth() / 2, top + getHeight() / 2)
    
    
    def getHeight(self):
        return bottom - top
    
    
    def getLeft(self):
        return left
    
    
    def getRight(self):
        return right
    
    
    def getSize(self):
        return getWidth() * getHeight()
    
    
    def getTop(self):
        return top
    
    
    def getWidth(self):
        return right - left
    
    
    def inBottomRight(self, location):
        Location center = getCenter()
        float distanceX = (float) (location.getLeft() - center.getLeft()) / getWidth()
        float distanceY = (float) (location.getTop() - center.getTop()) / getHeight()
        return distanceX + distanceY > 0
    
    
    def intersects(self, targetArea):
        if getRight() < targetArea.getLeft()  or  getLeft() > targetArea.getRight()
         or  getBottom() < targetArea.getTop()  or  getTop() > targetArea.getBottom()) {
            return False
        
        return True
    
    
    def intersects(self, location):
        return left <= location.getLeft()  and  location.getLeft() <= right  and  top <= location.getTop()
         and  location.getTop() <= bottom
    
    
    def moveTo(self, location):
        int deltaX = location.getLeft() - left
        int deltaY = location.getTop() - top
        left += deltaX
        right += deltaX
        top += deltaY
        bottom += deltaY
    
    
    """*
    * Textual representation of this area formatted as <code>[(left, top) - (right, bottom) ]</code>.
    * @return a string representation of this area
    """
    def toString(self):
        return "[ (" + getLeft() + ", " + getTop() + ") - (" + getRight() + ", " + getBottom() + ") ]"
    
    
    """*
    * Set bottom coordinate.
    *
    * @param bottom the bottom coordinate in pixels
    """
    def setBottom(self, bottom):
        self.bottom = bottom
    
    
    """*
    * Set left coordinate.
    *
    * @param left the left coordinate in pixels
    """
    def setLeft(self, left):
        self.left = left
    
    
    """*
    * Set right coordinate.
    *
    * @param right the right coordinate in pixels
    """
    def setRight(self, right):
        self.right = right
    
    
    """*
    * Set top coordinate.
    *
    * @param top the top coordinate in pixels
    """
    def setTop(self, top):
        self.top = top
    


