# Copyright (C) 2006-2008 Google Inc.
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

from pyjamas import DOM
from SimplePanel import SimplePanel
from pyjamas import Factory
from TabPanel import TabPanel
from TabBar import TabBar

"""
  
  A {@link SimplePanel} that wraps its contents in stylized boxes, which can be
  used to add rounded corners to a {@link Widget}.
  
  Wrapping a {@link Widget} in a "9-box" allows users to specify images in each
  of the corners and along the four borders. This method allows the content
  within the {@link DecoratorPanel} to resize without disrupting the look of
  the border. In addition, rounded corners can generally be combined into a
  single image file, which reduces the number of downloaded files at startup.
  This class also simplifies the process of using AlphaImageLoaders to support
  8-bit transparencies (anti-aliasing and shadows) in ie6, which does not
  support them normally.
  
  
  CSS Style Rules

  .gwt-DecoratorPanel { the panel }
  .gwt-DecoratorPanel .top { the top row }
  .gwt-DecoratorPanel .topLeft { the top left cell }
  .gwt-DecoratorPanel .topLeftInner { the inner element of the cell }
  .gwt-DecoratorPanel .topCenter { the top center cell }
  .gwt-DecoratorPanel .topCenterInner { the inner element of the cell }
  .gwt-DecoratorPanel .topRight { the top right cell }
  .gwt-DecoratorPanel .topRightInner { the inner element of the cell }
  .gwt-DecoratorPanel .middle { the middle row }
  .gwt-DecoratorPanel .middleLeft { the middle left cell }
  .gwt-DecoratorPanel .middleLeftInner { the inner element of the cell }
  .gwt-DecoratorPanel .middleCenter { the middle center cell }
  .gwt-DecoratorPanel .middleCenterInner { the inner element of the cell }
  .gwt-DecoratorPanel .middleRight { the middle right cell }
  .gwt-DecoratorPanel .middleRightInner { the inner element of the cell }
  .gwt-DecoratorPanel .bottom { the bottom row }
  .gwt-DecoratorPanel .bottomLeft { the bottom left cell }
  .gwt-DecoratorPanel .bottomLeftInner { the inner element of the cell }
  .gwt-DecoratorPanel .bottomCenter { the bottom center cell }
  .gwt-DecoratorPanel .bottomCenterInner { the inner element of the cell }
  .gwt-DecoratorPanel .bottomRight { the bottom right cell }
  .gwt-DecoratorPanel .bottomRightInner { the inner element of the cell }

"""
class DecoratorPanel(SimplePanel):
    #The default style name.
    DEFAULT_STYLENAME = "gwt-DecoratorPanel"

    #The default styles applied to each row.
    DEFAULT_ROW_STYLENAMES = [ "top", "middle", "bottom" ]

    def __init__(self, rowStyles=None, containerIndex=1, **kwargs):
        """ Creates a new panel using the specified style names to
            apply to each row.  Each row will contain three cells
            (Left, Center, and Right). The Center cell in the
            containerIndex row will contain the {@link Widget}.
            
            @param rowStyles an array of style names to apply to each row
            @param containerIndex the index of the container row
        """
      
        if rowStyles is None:
            rowStyles = self.DEFAULT_ROW_STYLENAMES

        if kwargs.has_key('Element'):
            self.table = kwargs.pop('Element')
            fc = DOM.getFirstChild(self.table)
            if fc:
                self.tbody = fc
            else:
                self.tbody = DOM.createTBody()
                DOM.appendChild(self.table, self.tbody)
        else:
            # Add a tbody
            self.table = DOM.createTable()
            self.tbody = DOM.createTBody()
            DOM.appendChild(self.table, self.tbody)
            DOM.setAttribute(self.table, "cellSpacing", "0")
            DOM.setAttribute(self.table, "cellPadding", "0")

        if not kwargs.has_key('StyleName'): kwargs['StyleName']=self.DEFAULT_STYLENAME
        SimplePanel.__init__(self, self.table, **kwargs)

        # Add each row
        for i in range(len(rowStyles)): 
            row = self.createTR(rowStyles[i])
            DOM.appendChild(self.tbody, row)
            if i == containerIndex:
                self.containerElem = DOM.getFirstChild(DOM.getChild(row, 1))

    def createTR(self, styleName) :
        """ Create a new row with a specific style name. The row
            will contain three cells (Left, Center, and Right), each
            prefixed with the specified style name.
         
            This method allows Widgets to reuse the code on a DOM
            level, without creating a DecoratorPanel Widget.
         
            @param styleName the style name
            @return the new row {@link Element}
        """
        trElem = DOM.createTR()
        self.setStyleName(trElem, styleName)
        DOM.appendChild(trElem, self.createTD(styleName + "Left"))
        DOM.appendChild(trElem, self.createTD(styleName + "Center"))
        DOM.appendChild(trElem, self.createTD(styleName + "Right"))
        return trElem

    def createTD(self, styleName) :
        """ Create a new table cell with a specific style name.
         
            @param styleName the style name
            @return the new cell {@link Element}
        """
        tdElem = DOM.createTD()
        inner = DOM.createDiv()
        DOM.appendChild(tdElem, inner)
        self.setStyleName(tdElem, styleName)
        self.setStyleName(inner, styleName + "Inner")
        return tdElem

    def getCellElement(self, row, cell) :
      """   Get a specific Element from the panel.
       
        @param row the row index
        @param cell the cell index
        @return the Element at the given row and cell
      """
      tr = DOM.getChild(self.tbody, row)
      td = DOM.getChild(tr, cell)
      return DOM.getFirstChild(td)

    def getContainerElement(self):
        return self.containerElem

Factory.registerClass('pyjamas.ui.DecoratorPanel', DecoratorPanel)

class DecoratedTabBar(TabBar):

    TAB_ROW_STYLES = ["tabTop", "tabMiddle"]

    STYLENAME_DEFAULT = "gwt-DecoratedTabBar"

    def __init__(self, **kwargs):
        """ Creates an empty {@link DecoratedTabBar}.
        """
        TabBar.__init__(self, **kwargs)

    def createTabTextWrapper(self):
        return DecoratorPanel(self.TAB_ROW_STYLES, 1)

Factory.registerClass('pyjamas.ui.DecoratedTabBar', DecoratedTabBar)

class DecoratedTabPanel(TabPanel):
    DEFAULT_STYLENAME = "gwt-DecoratedTabPanel"

    def __init__(self, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']=self.DEFAULT_STYLENAME
        TabPanel.__init__(self, DecoratedTabBar(), **kwargs)

        self.getTabBar().setStyleName(DecoratedTabBar.STYLENAME_DEFAULT)

    def createTabTextWrapper(self):
        return DecoratorPanel(DecoratedTabBar.TAB_ROW_STYLES, 1)

Factory.registerClass('pyjamas.ui.DecoratedTabPanel', DecoratedTabPanel)

class DecoratorTitledPanel(DecoratorPanel):

    def __init__(self, title, titleStyle=None, imgStyle=None,
                             rowStyles=None,
                             containerIndex=2, titleIndex=1,
                             **kwargs) :
        if rowStyles is None:
            rowStyles = ["top", "top2", "middle", "bottom"]

        if titleStyle is None:
            titleStyle = "title"

        DecoratorPanel.__init__(self, rowStyles, containerIndex, **kwargs)

        inner = self.getCellElement(titleIndex, 1)
        if imgStyle:
            img = DOM.createDiv()
            DOM.setAttribute(img, "className", imgStyle)
            DOM.appendChild(inner, img)
        tdiv = DOM.createDiv()
        DOM.setAttribute(tdiv, "className", titleStyle)
        DOM.setInnerText(tdiv, title)
        DOM.appendChild(inner, tdiv)

Factory.registerClass('pyjamas.ui.DecoratorTitledPanel', DecoratorTitledPanel)

