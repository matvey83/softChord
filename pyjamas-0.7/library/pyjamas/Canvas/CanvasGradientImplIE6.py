"""
* Copyright 2008 Google Inc.
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

import math



from pyjamas.Canvas.ColorStop import ColorStop

"""*
* Gradients for IE6 implementation need some extra meta info.
"""
class CanvasGradientImplIE6:
    def __init__(self, x0, y0, x1, y1):
        self.startX = x0
        self.startY = y0
        self.endX = x1
        self.endY = y1
        self.startRad = 0
        self.endRad = 0
        self.dx = x1 - x0
        self.dy = y1 - y0
        self.length =  math.sqrt((self.dx * self.dx) + (self.dy * self.dy))
        self.angle = int(math.atan(self.dx / self.dy) * 180 / math.pi) + 180
        
        self.colorStops = []
    
    def addColorStop(self, offset, color):
        newColorStop = ColorStop(offset, color)
        for i in range(len(self.colorStops)):
            cs = self.colorStops[i]
            if offset < cs.offset:
                self.colorStops.append(i, newColorStop)
                return
            
        self.colorStops.append(newColorStop)
    
    
    """*
    * Creates an equivalent copy of this Gradient object.
    *
    * @return returns an equivalent copy of this gradient object
    """
    def cloneGradient(self):
        pass

