class GWTCanvas(Widget):
    
    def getCanvasImpl(self):
        return GWTCanvasImplIE6()
    def createLinearGradient(self, x0, y0, x1, y1):
        return LinearGradientImplIE6(x0, y0, x1, y1)# , self.getElement())
    def createRadialGradient(self, x0, y0, r0, x1, y1, r1):
        return RadialGradientImplIE6(x0, y0, r0, x1, y1, r1)#,self.getElement())


