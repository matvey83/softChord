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
* Class representing a location defined by left (x) and top (y) coordinates.
"""
class Location:
    def getLeft(self):
        """*
        * Get x coordinate.
        *
        * @return the left offset in pixels
        """
        pass

    def getTop(self):
        """*
        * Get the y coordinate.
        *
        * @return the top offset in pixels
        """
        pass
    
    def newLocationSnappedToGrid(self, gridX, gridY):
        """*
        * Return a location, snapped to the grid based on a spacing
        * of <code>(gridX, gridY)</code>.
        *
        * @param gridX the horizontal grid spacing in pixels
        * @param gridY the vertical grid spacing in pixels
        * @return the location
        """
        pass

