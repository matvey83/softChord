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

from pyjamas.Canvas.CanvasGradientImplIE6 import CanvasGradientImplIE6 

"""*
*  IE6 deferred binding of Gradient Factory will create instances of this class
*  for RadialGradients.
"""
class RadialGradientImplIE6 (CanvasGradientImplIE6):
    
    def __init__(self, x0, y0, r0, x1, y1, r1):
        CanvasGradientImplIE6.__init__(self, x0,y0,x1,y1)
        self.startRad = r0
        self.endRad = r1
        self.type = "gradientradial"
    
    
    def cloneGradient(self):
        newGrad = RadialGradientImplIE6(self.startX,self.startY,
                         self.startRad,
                         self.endX,self.endY,
                         self.endRad)
        newGrad.startX = self.startX
        newGrad.startY = self.startY
        newGrad.startRad = self.startRad
        newGrad.endX = self.endX
        newGrad.endY = self.endY
        newGrad.endRad = self.endRad
        
        cStops = self.colorStops
        
        for i in range(len(cStops)):
            newGrad.colorStops.append(cStops[i].cloneColorStop())
        
        return newGrad
    
    


