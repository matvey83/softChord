from pyjamas.Canvas2D import Canvas
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.DOM import getFirstChild
from pyjamas import Window
import math
from __pyjamas__ import jsinclude

# Include the processing.js in the module scope
jsinclude("processing.js")
from __javascript__ import Processing # defined by processing.js

p = None
radius = 50.0
delay = 16

def setup():
    global p,radius,delay,X,Y,nX,nY
    p.size(200,200)
    p.strokeWeight( 10 )
    p.frameRate( 15 )
    X = p.width / 2
    Y = p.width / 2
    nX = X
    nY = Y  

def draw():
    global p,radius,delay,X,Y,nX,nY
    radius = radius + math.sin( p.frameCount / 4 )
    X+=(nX-X)/delay
    Y+=(nY-Y)/delay
    p.background( 100 )
    p.fill( 0, 121, 184 )
    p.stroke(255)
    p.ellipse(X, Y, radius, radius )
    
def mouseMoved():
    global p,nX,nY
    nX = p.mouseX
    nY = p.mouseY

class ProcessingCanvas(Canvas):
    def __init__(self):
        Canvas.__init__(self,0,0)
        self.c = getFirstChild(self.getElement())
        self.p = Processing (self.c)
        global p
        p = self.p
    
if __name__ == '__main__':
    PC = ProcessingCanvas()
    PC.p.setup = setup
    PC.p.draw = draw
    PC.p.mouseMoved = mouseMoved
    PC.p.init()
    RootPanel().add(PC)

