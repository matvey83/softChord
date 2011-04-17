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


from pyjamas.Canvas import GWTCanvasConsts
from pyjamas.Canvas import GWTCanvasImplIEConsts

"""*
* The VML context abstraction for the Internet Explorer implementation.
"""
class VMLContext:

    def __init__(self, ctx=None):


        if ctx is None:

            # load identity matrix
            self.matrix = [1, 0, 0,
                           0, 1, 0,
                           0, 0, 1]

            # init other stuff
            self.arcScaleX         =  1
            self.arcScaleY         =  1
            self.globalAlpha         =  1
            self.strokeAlpha         =  1
            self.fillAlpha         =  1
            self.miterLimit          = 10
            self.lineWidth         =  1
            self.lineCap           =  GWTCanvasImplIEConsts.BUTT
            self.lineJoin          =  GWTCanvasConsts.MITER
            self.strokeStyle         =  "#000"
            self.fillStyle         =  "#000"
            self.fillGradient = None
            self.strokeGradient = None
            self.globalCompositeOperation  =  GWTCanvasImplIEConsts.SOURCE_OVER

            return

        # copy the matrix
        self.matrix = []
        for i in range(9):
            self.matrix.append(ctx.matrix[i])

        # copy other stuff
        self.arcScaleX         = ctx.arcScaleX
        self.arcScaleY         = ctx.arcScaleY
        self.globalAlpha         = ctx.globalAlpha
        self.strokeAlpha         = ctx.strokeAlpha
        self.fillAlpha         = ctx.fillAlpha
        self.miterLimit          = ctx.miterLimit
        self.lineWidth         = ctx.lineWidth
        self.lineCap           = ctx.lineCap
        self.lineJoin          = ctx.lineJoin
        self.strokeStyle         = ctx.strokeStyle
        self.fillStyle         = ctx.fillStyle
        self.fillGradient = ctx.fillGradient
        self.strokeGradient = ctx.strokeGradient
        self.globalCompositeOperation  = ctx.globalCompositeOperation



