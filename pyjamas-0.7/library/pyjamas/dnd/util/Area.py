"""
* Copyright 2007 Fred Sauer
*
* Licensed under the Apache License, Version 2.0 (self, the "License"); you may not
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
* Class representing a rectangular region, with convenience methods for
* calculations.
"""
class Area:
    """*
    * Clone our area.
    *
    * @return the area
    """
    def copyOf(self):
        pass
    
    """*
    * Determine the shortest distance from the location to the edge of the area.
    * Zero indicates a location on the edge. Negative distances indicate a
    * location inside the area.
    *
    * @param location the reference location
    * @return shortest distance to edge of area
    """
    def distanceToEdge(self,  location):
        pass
    
    """*
    * Get the area's bottom coordinate in pixels.
    *
    * @return the bottom coordinate in pixels
    """
    def getBottom(self):
        pass
    
    """*
    * Get the area's center Location.
    *
    * @return the area's center Location
    """
    def getCenter(self):
        pass
    
    """*
    * Get the area's height
    *
    * @return the area's height in pixels
    """
    def getHeight(self):
        pass
    
    """*
    * Get the area's left coordinate in pixels.
    *
    * @return the left coordinate in pixels
    """
    def getLeft(self):
        pass
    
    """*
    * Get the area's right coordinate in pixels.
    *
    * @return the right coordinate in pixels
    """
    def getRight(self):
        pass
    
    """*
    * Determine area (self, width * height).
    *
    * @return size of area
    """
    def getSize(self):
        pass
    
    """*
    * Get the area's top coordinate in pixels.
    *
    * @return the top coordinate in pixels
    """
    def getTop(self):
        pass
    
    """*
    * Get the area's width
    *
    * @return the area's width in pixels
    """
    def getWidth(self):
        pass
    
    """*
    * Determine if location is to the bottom-right of the following 45 degree
    * line.
    *
    * <pre>
    *             y  45
    *             | /
    *             |/
    *        -----+----- x
    *            /|
    *           / |
    *
    * </pre>
    *
    * @param location the location to consider
    * @return True if the location is to below the 45 degree line
    """
    def inBottomRight(self, location):
        pass
    
    """*
    * Determine if the target area intersects our area
    *
    * @param targetArea the area to compare to
    * @return True if target area intersects our area
    """
    def intersects(self, targetArea):
        pass
    
    """*
    * Determine if the provided location intersects with our area.
    *
    * @param location the location to examine
    * @return True if the location falls within our area
    """
    def intersects(self, location):
        pass
    
    """*
    * Translate our top left position to the location.
    *
    * @param location the position to translate to
    """
    def moveTo(self, location):
        pass

