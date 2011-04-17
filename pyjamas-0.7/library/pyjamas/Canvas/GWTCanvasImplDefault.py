"""
* Copyright 2008 Google Inc.
*
* Licensed under the Apache License, Version 2.0 (the "License") you may not
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




from pyjamas import DOM
from pyjamas import log
from pyjamas.ui.Widget import Widget

from pyjamas.Canvas.Color import Color

def cvt(s):
    return s

"""*
* Deferred binding implementation of GWTCanvas.
"""
class GWTCanvasImplDefault:

    def __init__(self):
        self.canvasContext = None

    def arc(self, x, y, radius, startAngle, endAngle, antiClockwise):
        self.canvasContext.arc(x,y,radius,startAngle,endAngle,antiClockwise)


    def beginPath(self):
        self.canvasContext.beginPath()


    def clear(self, width, height):
        self.clearRect(0,0,width,height)


    def closePath(self):
        self.canvasContext.closePath()


    def createElement(self):
        e = DOM.createElement("CANVAS")
        self.setCanvasContext(e.getContext('2d'))
        return e


    def cubicCurveTo(self, cp1x, cp1y, cp2x, cp2y, x, y):
        self.canvasContext.bezierCurveTo(cp1x,cp1y,cp2x,cp2y,x,y)


    def drawImage(self, img, sourceX, sourceY, sourceWidth=None, sourceHeight=None, destX=None, destY=None, destWidth=None, destHeight=None):

        if isinstance(img, Widget):
            img = img.getElement()
        if sourceWidth is None:
            self.canvasContext.drawImage(img,sourceX,sourceY)
        else:
            self.canvasContext.drawImage(img,sourceX,sourceY,sourceWidth,sourceHeight,destX,destY,destWidth,destHeight)



    def fill(self):
        self.canvasContext.fill()


    def fillRect(self, startX, startY, width, height):
        self.canvasContext.fillRect(startX,startY,width,height)


    def getGlobalAlpha(self):
        return self.canvasContext.globalAlpha


    def getGlobalCompositeOperation(self):
        return self.canvasContext.globalCompositeOperation


    def getHeight(self, elem):
        return DOM.getElementPropertyInt(elem, "height")


    def getLineCap(self):
        return self.canvasContext.lineCap


    def getLineJoin(self):
        return self.canvasContext.lineJoin


    def getLineWidth(self):
        return self.canvasContext.lineWidth


    def getMiterLimit(self):
        return self.canvasContext.miterLimit


    def getWidth(self, elem):
        return DOM.getElementPropertyInt(elem, "width")


    def lineTo(self, x, y):
        self.canvasContext.lineTo(x,y)


    def moveTo(self, x, y):
        self.canvasContext.moveTo(x,y)


    def quadraticCurveTo(self, cpx, cpy, x, y):
        self.canvasContext.quadraticCurveTo(cpx,cpy,x,y)


    def rect(self, x, y, width, height):
        self.canvasContext.rect(x,y,width,height)


    def restoreContext(self):
        self.canvasContext.restore()


    def rotate(self, angle):
        self.canvasContext.rotate(angle)


    def saveContext(self):
        self.canvasContext.save()


    def scale(self, x, y):
        self.canvasContext.scale(x,y)


    def setBackgroundColor(self, element, color):
        DOM.setStyleAttribute(element, "backgroundColor", color)


    def setCoordHeight(self, elem, height):
        DOM.setElemAttribute(elem, "height", str(height))


    def setCoordWidth(self, elem, width):
        DOM.setElemAttribute(elem,"width", str(width))


    def setStrokeStyle(self, gradient):
        if isinstance(gradient, Color): # is it a colorString?
            gradient = str(gradient)
        elif not isinstance(gradient, str): # is it a colorString?
            gradient = gradient.getObject() # it's a gradient object
        self.canvasContext.strokeStyle = cvt(gradient)


    def setFillStyle(self, gradient):
        if isinstance(gradient, Color): # is it a colorString?
            gradient = str(gradient)
        elif not isinstance(gradient, str): # is it a colorString?
            gradient = gradient.getObject() # it's a gradient object
        self.canvasContext.fillStyle = cvt(gradient)

    def setGlobalAlpha(self, alpha):
        self.canvasContext.globalAlpha = alpha


    def setGlobalCompositeOperation(self, globalCompositeOperation):
        self.canvasContext.globalCompositeOperation = cvt(globalCompositeOperation)


    def setLineCap(self, lineCap):
        self.canvasContext.lineCap = cvt(lineCap)


    def setLineJoin(self, lineJoin):
        self.canvasContext.lineJoin = cvt(lineJoin)


    def setLineWidth(self, width):
        self.canvasContext.lineWidth = width


    def setMiterLimit(self, miterLimit):
        self.canvasContext.miterLimit = miterLimit


    def setPixelHeight(self, elem, height):
        DOM.setStyleAttribute(elem, "height", "%dpx" % height)


    def setPixelWidth(self, elem, width):
        DOM.setStyleAttribute(elem, "width", "%dpx" % width)


    def stroke(self):
        self.canvasContext.stroke()


    def strokeRect(self, startX, startY, width, height):
        self.canvasContext.strokeRect(startX,startY,width,height)

    def transform(self, m11, m12, m21, m22, dx, dy):
        self.canvasContext.transform(m11,m12,m21,m22,dx,dy)


    def translate(self, x, y):
        self.canvasContext.translate(x,y)


    def clearRect(self, startX, startY, width, height):
        self.canvasContext.clearRect(startX,startY,width,height)


    def setCanvasContext(self, ctx):
        self.canvasContext = ctx




