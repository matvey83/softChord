""" 
    Copyright (C) 2008, 2009 - Luke Kenneth Casson Leighton <lkcl@lkcl.net>
  
"""
from pyjamas import DOM
from pyjamas.ui import Event

class ClickHandler(object):

    def __init__(self, preventDefault=False):
        self._clickListeners = []
        self._doubleclickListeners = []
        self._clickPreventDefault = preventDefault
        
        self.sinkEvents(Event.ONCLICK)
        self.sinkEvents(Event.ONDBLCLICK)

    def onClick(self, sender=None):
        pass

    def onDoubleClick(self, sender=None):
        pass

    def addDoubleClickListener(self, listener):
        self._doubleclickListeners.append(listener)

    def addClickListener(self, listener):
        self._clickListeners.append(listener)

    def onBrowserEvent(self, event):
        """Listen to events raised by the browser and call the appropriate 
        method of the listener (widget, ..) object. 
        """
        type = DOM.eventGetType(event)
        if type == "click":
            if self._clickPreventDefault:
                DOM.eventPreventDefault(event)
            for listener in self._clickListeners:
                if hasattr(listener, "onClick"):
                    listener.onClick(self)
                else:
                    listener(self)
        elif type == "dblclick":
            if self._clickPreventDefault:
                DOM.eventPreventDefault(event)
            for listener in self._doubleclickListeners:
                if hasattr(listener, "onDoubleClick"):
                    listener.onDoubleClick(self)
                else:
                    listener(self)

    def removeClickListener(self, listener):
        self._clickListeners.remove(listener)

    def removeDoubleClickListener(self, listener):
        self._doubleclickListeners.remove(listener)

