# Tooltip component for Pyjamas
# Ported by Willie Gollino from Tooltip component for GWT - Originally by Alexei Sokolov http://gwt.components.googlepages.com/
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

from PopupPanel import PopupPanel
from pyjamas import Factory
from HTML import HTML
from RootPanel import RootPanel
from pyjamas.Timer import Timer

tooltip_hide_timer = None

class Tooltip(PopupPanel):
    def __init__(self, sender, offsetX, offsetY, contents,
                       show_delay, hide_delay, styleName, **kwargs):
        """ contents may be a text string or it may be a widget
        """
        PopupPanel.__init__(self, True, **kwargs)
        self.show_delay = show_delay
        self.hide_delay = hide_delay
        
        if isinstance(contents, str):
            contents = HTML(contents)
        self.add(contents)

        left = sender.getAbsoluteLeft() + offsetX
        top = sender.getAbsoluteTop() + offsetY

        self.setPopupPosition(left, top)
        self.setStyleName(styleName)

        if tooltip_hide_timer:
            self.tooltip_show_timer = Timer(1, self)
        else:
            self.tooltip_show_timer = Timer(self.show_delay, self)
        
    def show(self):
        global tooltip_hide_timer
        
        # activate fast tooltips
        tooltip_hide_timer = Timer(self.hide_delay, self)
        PopupPanel.show(self)

    def hide(self, autoClosed=False):
        self.tooltip_show_timer.cancel()
        PopupPanel.hide(self, autoClosed)

    def onTimer(self, tooltip_id):
        global tooltip_hide_timer

        # deactivate fast tooltips on last timer
        if tooltip_hide_timer and tooltip_id == tooltip_hide_timer.getID():
            tooltip_hide_timer = None

        if tooltip_id == self.tooltip_show_timer.getID():
            self.show()
        else:
            self.hide()


class TooltipListener:
    DEFAULT_TOOLTIP_STYLE = "TooltipPopup"
    DEFAULT_OFFSET_X = 10
    DEFAULT_OFFSET_Y = 35

    def __init__(self, text, show_delay = 1000, hide_delay = 5000, styleName = ""):
        if not styleName:
            styleName = TooltipListener.DEFAULT_TOOLTIP_STYLE
        
        self.tooltip = None
        self.text = text
        self.styleName = styleName
        self.show_delay = show_delay
        self.hide_delay = hide_delay
        self.offsetX = TooltipListener.DEFAULT_OFFSET_X
        self.offsetY = TooltipListener.DEFAULT_OFFSET_Y

    def onMouseEnter(self, sender):
        if self.tooltip is not None:
            self.tooltip.hide()
        self.tooltip = Tooltip(sender, self.offsetX, self.offsetY, self.text, self.show_delay, self.hide_delay, self.styleName)

    def onMouseLeave(self, sender):
        if self.tooltip is not None:
            self.tooltip.hide()

    def onMouseMove(self, sender, x, y):
        pass
        
    def onMouseDown(self, sender, x, y):
        pass
    
    def onMouseUp(self, sender, x, y):
        pass

    def getStyleName(self):
        return self.styleName

    def setStyleName(self, styleName):
        self.styleName = styleName

    def getOffsetX(self):
        return self.offsetX

    def setOffsetX(self, offsetX):
        self.offsetX = offsetX

    def getOffsetY(self):
        return self.offsetY

    def setOffsetY(self, offsetY):
        self.offsetY = offsetY

Factory.registerClass('pyjamas.ui.Tooltip', Tooltip)

