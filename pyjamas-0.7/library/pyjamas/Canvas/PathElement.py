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

"""*
* Simple Path String generator class.
"""

"""*
* Path Constants.
"""
ARC = " ar"
CLOSE = " x"
END = " e"
LINETO = " l"
MOVETO = " m"
CUBIC = " c"

def arc(x, y, radius, startAngle, endAngle, antiClockwise, canvas):
    
    matrix = canvas.matrix
    context = canvas.context
    
    if not antiClockwise:
        realStartAngle = endAngle
        realEndAngle = startAngle
    else:
        realStartAngle = startAngle
        realEndAngle = endAngle
    
    ar = radius * 10
    startX = (x + math.cos(realStartAngle) * ar - 5)
    startY = (y + math.sin(realStartAngle) * ar - 5)
    endX = (x + math.cos(realEndAngle) * ar - 5)
    endY = (y + math.sin(realEndAngle) * ar - 5)
    if startX == endX  and  not antiClockwise:
        startX += 0.125
    
    
    cx = canvas.getCoordX(matrix, x, y)
    cy = canvas.getCoordY(matrix, x, y)
    arcX = (context.arcScaleX * ar)
    arcY = (context.arcScaleY * ar)
    return (ARC + str(int(math.floor((cx - arcX + 0.5)))) + ","
        + str(int(math.floor(cy + arcY + 0.5))) + " "
        + str(int(math.floor(cx + arcX + 0.5))) + ","
        + str(int(math.floor(cy - arcY + 0.5))) + " "
        + str(canvas.getCoordX(matrix, startX, startY)) + ","
        + str(canvas.getCoordY(matrix, startX, startY)) + " "
        + str(canvas.getCoordX(matrix, endX, endY)) + ","
        + str(canvas.getCoordY(matrix, endX, endY)))


def bezierCurveTo(c1x, c1y, c2x, c2y, x, y, canvas):
    matrix = canvas.matrix
    return (CUBIC + str(canvas.getCoordX(matrix, c1x, c1y)) + ","
        + str(canvas.getCoordY(matrix, c1x, c1y)) + ","
        + str(canvas.getCoordX(matrix, c2x, c2y)) + ","
        + str(canvas.getCoordY(matrix, c2x, c2y)) + ","
        + str(canvas.getCoordX(matrix, x, y)) + ","
        + str(canvas.getCoordY(matrix, x, y)))


def closePath():
    return CLOSE


def lineTo(x, y, canvas):
    matrix = canvas.matrix
    return (LINETO + str(canvas.getCoordX(matrix, x, y)) + ","
        + str(canvas.getCoordY(matrix, x, y)))


def moveTo(x, y, canvas):
    matrix = canvas.matrix
    return (MOVETO + str(canvas.getCoordX(matrix, x, y)) + ","
            + str(canvas.getCoordY(matrix, x, y)))


