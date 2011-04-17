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

from pyjamas.Canvas.CanvasGradientImplDefault import CanvasGradientImplDefault 


"""*
*  Default deferred binding of Gradient Factory will create instances of this class
*  for RadialGradients.
"""
class RadialGradientImplDefault(CanvasGradientImplDefault):
    
    def __init__(self, x0, y0, r0, x1, y1, r1, c):
        CanvasGradientImplDefault.__init__(self)
        self.createNativeGradientObject(x0,y0,r0,x1,y1,r1, c)
    
    def createNativeGradientObject(self, x0, y0, r0, x1, y1, r1, c):
        ctx = c.getContext('2d')
        gradient = ctx.createRadialGradient(x0,y0,r0,x1,y1,r1)
        self.setNativeGradient(gradient)
    

