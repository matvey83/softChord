""" Control Widgets.  Presently comprises a Vertical Slider Demo and derivatives.

    HorizontalDemoSlider and HorizontalDemoSlider2 added by Bill Winder 
    AreaDemoSlider and AreaDemoSlider2 added by Bill Winder 

    Copyright (C) 2008, 2009, 2010 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
    Copyright (C) 2010 - Cedric Gestes <gestes@aldebaran-robotics.com>
    Copyright (C) 2009, 2010 - Bill Winder <wgwinder@gmail.com> 


    To do: All controls with draggable=True do not fire the OnFocus methon on single click.  
    the control does not activate the OnFocus method. Clicking the handle does fire OnFocus, however.

"""

from pyjamas import Factory
import math
from pyjamas import DOM
from pyjamas import Window
from FocusWidget import FocusWidget
from MouseListener import MouseHandler
from pyjamas.ui import Event
from pyjamas.ui import Focus
from pyjamas.ui import KeyboardListener

from TextBox import TextBox

class Control(FocusWidget, MouseHandler):

    def __init__(self, element, min_value, max_value,
                       start_value=None, step=None,
                       **kwargs):

        self.min_value = min_value
        self.max_value = max_value
        if start_value is None:
            start_value = min_value
        if step is None:
            step = (self.max_value - self.min_value) / 20
        self.step = step
        self.value = start_value
        self.valuechange_listeners = []
        self.dragging = False
        self.drag_enabled = False

        if not kwargs.has_key("TabIndex"): kwargs['TabIndex'] = 0
        FocusWidget.__init__(self, element, **kwargs)
        MouseHandler.__init__(self)

    def onFocus(self, sender):
        pass

    def onLostFocus(self, sender):
        pass

    def onClick(self, sender=None):
        pass

    def processValue(self, value):
        """ rounds and limits the value to acceptable range
        """
        value = math.floor((value - self.min_value) / self.step)
        value = (value * self.step) + self.min_value
        value = max(value, self.min_value)
        value = min(value, self.max_value)
        return value

    def setValue(self, new_value, notify=1):

        old_value = self.value
        self.value = new_value

        if not notify:
            return

        for listener in self.valuechange_listeners:
            listener.onControlValueChanged(self, old_value, new_value)

    def addControlValueListener(self, listener):
        self.valuechange_listeners.append(listener)

    def removeControlValueListener(self, listener):
        self.valuechange_listeners.remove(listener)

    def moveControl(self, x, y):
        pass

    def onClick(self, sender=None):
        self.setFocus(True)
        # work out the relative position of cursor
        event = DOM.eventGetCurrentEvent()
        mouse_x = DOM.eventGetClientX(event) + Window.getScrollLeft()
        mouse_y = DOM.eventGetClientY(event) + Window.getScrollTop()
        self.moveControl(mouse_x - self.getAbsoluteLeft(),
                         mouse_y - self.getAbsoluteTop())

    def onMouseMove(self, sender, x, y):
        if not self.dragging:
            return
        self.moveControl(x + Window.getScrollLeft(), y + Window.getScrollTop())

    def onLoseFocus(self, sender):
        self.dragging = False
        DOM.releaseCapture(self.getElement())


    def onMouseDown(self, sender, x, y):
        # regardless of drag_enabled, onMouseDown must prevent
        # default, in order to avoid losing focus.
        DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
        if not self.drag_enabled:
            return
        self.dragging = True
        DOM.setCapture(self.getElement())
        self.moveControl(x + Window.getScrollLeft(), y + Window.getScrollTop())

    def onMouseUp(self, sender, x, y):
        self.dragging = False
        DOM.releaseCapture(self.getElement())

    def onMouseEnter(self, sender):
        pass
    def onMouseLeave(self, sender):
        pass

    def onKeyDown(self, sender, keycode, modifiers):
        if keycode == KeyboardListener.KEY_UP:
            DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
            new_value = self.processValue(self.value + self.step)
            self.setControlPos(new_value)
            self.setValue(new_value)
        elif keycode == KeyboardListener.KEY_DOWN:
            DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
            new_value = self.processValue(self.value - self.step)
            self.setControlPos(new_value)
            self.setValue(new_value)

    def onKeyUp(self, sender, keycode, modifiers):
        pass

    def onKeyPress(self, sender, keycode, modifiers):
        pass

Factory.registerClass('pyjamas.ui.Control', Control)


class DControl(Control):

    def __init__(self, element, (min_value_x, min_value_y),
                                (max_value_x, max_value_y),
                       start_value_xy=None, step_xy=None, **kwargs):

        self.min_value_x = min_value_x
        self.min_value_y = min_value_y

        self.max_value_x = max_value_x
        self.max_value_y = max_value_y

        if start_value_xy is None:
            self.start_value_x = min_value_x
            self.start_value_y = min_value_y
        else:
            (self.start_value_x, self.start_value_y) = start_value_xy

        if step_xy is None:
            self.step_x = (self.max_value_x - self.min_value_x) / 20
            self.step_y = (self.max_value_y - self.min_value_y) / 20        
        else:
            self.step_x,self.step_y=step_xy

        self.value_x = self.start_value_x
        self.value_y = self.start_value_y

        self.valuechange_listeners = []
        self.dragging = False
        self.drag_enabled = False

        if not kwargs.has_key("TabIndex"): kwargs['TabIndex'] = 0
        FocusWidget.__init__(self, element, **kwargs)
        MouseHandler.__init__(self)

    def processValue(self, (value_x,value_y)):
        """ rounds and limits the value to acceptable range
        """
        value_x = math.floor((value_x - self.min_value_x) / self.step_x)
        value_x = (value_x * self.step_x) + self.min_value_x
        value_x = max(value_x, self.min_value_x)
        value_x = min(value_x, self.max_value_x)

        value_y = math.floor((value_y - self.min_value_y) / self.step_y)
        value_y = (value_y * self.step_y) + self.min_value_y
        value_y = max(value_y, self.min_value_y)
        value_y = min(value_y, self.max_value_y)    

        return (value_x,value_y)

    def setValue(self, (new_value_x,new_value_y), notify=1):

        old_value_x = self.value_x
        self.value_x = new_value_x

        old_value_y = self.value_y
        self.value_y = new_value_y    

        if not notify:
            return

        for listener in self.valuechange_listeners:
            listener.onControlValueChanged(self, (old_value_x,old_value_y),
                                                 (new_value_x,new_value_y))

    def onControlValueChanged(self, value_old_xy, value_new_xy):
        pass

    def onKeyDown(self, sender, keycode, modifiers):
        if keycode == KeyboardListener.KEY_UP:
            DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
            new_value_x, new_value_y = \
                self.processValue((self.value_x + self.step_x,
                                   self.value_y + self.step_y))
            self.setControlPos((new_value_x,new_value_y))
            self.setValue((new_value_x, new_value_y))
        elif keycode == KeyboardListener.KEY_DOWN:
            DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
            new_value_x, new_value_y = \
               self.processValue((self.value_x - self.step_x,
                                  self.value_y-self.step_y))
            self.setControlPos((new_value_x, new_value_y))
            self.setValue((new_value_x, new_value_y))

Factory.registerClass('pyjamas.ui.DControl', DControl)


class VerticalDemoSlider(Control):

    def __init__(self, min_value, max_value, start_value=None, step=None,
                       **kwargs):

        if not kwargs.has_key("StyleName"): 
            kwargs['StyleName'] = "gwt-VerticalSlider"

        if kwargs.has_key('Element'):
            # XXX FIXME: Focus.createFocusable is here for a reason...
            element = kwargs.pop('Element')
        else:
            element = Focus.createFocusable()
        DOM.setStyleAttribute(element, "position", "relative")
        DOM.setStyleAttribute(element, "overflow", "hidden")

        self.handle = DOM.createDiv()
        DOM.appendChild(element, self.handle)

        DOM.setStyleAttribute(self.handle, "border", "1px")
        DOM.setStyleAttribute(self.handle, "width", "100%")
        DOM.setStyleAttribute(self.handle, "height", "10px")
        DOM.setStyleAttribute(self.handle, "backgroundColor", "#808080")

        Control.__init__(self, element, min_value, max_value, start_value, step,
                               **kwargs)

        self.addClickListener(self)
        self.addFocusListener(self)
        self.addMouseListener(self)

    def onFocus(self, sender):
        self.addStyleName("gwt-VerticalSlider-focussed")

    def onLostFocus(self, sender):
        self.removeStyleName("gwt-VerticalSlider-focussed")
        self.dragging = False
        DOM.releaseCapture(self.getElement())
    def moveControl(self, mouse_x, mouse_y):

        handle_height = DOM.getIntAttribute(self.handle, "offsetHeight")
        widget_height = self.getOffsetHeight()
        height_range = widget_height - 10 # handle height is hard-coded
        relative_y = mouse_y - (handle_height / 2)
        if relative_y < 0:
            relative_y = 0
        if relative_y >= height_range:
            relative_y = height_range

        relative_y = height_range - relative_y # turn round (bottom to top)

        val_diff = self.max_value - self.min_value
        new_value = ((val_diff * relative_y) / height_range) + self.min_value
        new_value = self.processValue(new_value)

        self.setControlPos(new_value)
        self.setValue(new_value)

    def setControlPos(self, value):

        widget_height = self.getOffsetHeight()
        height_range = widget_height - 10 # handle height is hard-coded
        val_diff = self.max_value - self.min_value
        relative_y = height_range * (value - self.min_value) / val_diff

        # limit the position to be in the widget!
        if relative_y < 0:
            relative_y = 0
        if relative_y >= height_range:
            relative_y = height_range

        relative_y = height_range - relative_y # turn round (bottom to top)

        # move the handle
        DOM.setStyleAttribute(self.handle, "top", "%dpx" % relative_y)
        DOM.setStyleAttribute(self.handle, "position", "absolute")

Factory.registerClass('pyjamas.ui.VerticalDemoSlider', VerticalDemoSlider)


class VerticalDemoSlider2(VerticalDemoSlider):

    def __init__(self, min_value, max_value, start_value=None, **kwargs):

        VerticalDemoSlider.__init__(self, min_value, max_value, start_value,
                                    **kwargs)
        self.addKeyboardListener(self)
        self.drag_enabled = True

Factory.registerClass('pyjamas.ui.VerticalDemoSlider2', VerticalDemoSlider2)


class InputControl(Control):

    def __init__(self, min_value, max_value, start_value=None, step=None,
                       **kwargs):

        if not kwargs.has_key("StyleName"):
            kwargs['StyleName'] = "gwt-InputControl"
        self.input = TextBox()
        self.input.addKeyboardListener(self)
        #element = DOM.createDiv()
        if kwargs.has_key('Element'):
            # XXX FIXME: unlikely to work!
            element = kwargs.pop('Element')
        else:
            element = self.input.getElement() # YUK!!!
        Control.__init__(self, element, min_value, max_value, start_value, step,
                               **kwargs)

        self.addClickListener(self)
        self.addFocusListener(self)
        self.addKeyboardListener(self)

    def onFocus(self, sender):
        self.addStyleName("gwt-InputControl-focussed")

    def onLostFocus(self, sender):
        self.removeStyleName("gwt-InputControl-focussed")

    def setControlPos(self, value):

        self.input.setText(value)

    def onKeyPress(self, sender, keycode, modifiers):
        if keycode == KeyboardListener.KEY_ENTER:
            DOM.eventPreventDefault(DOM.eventGetCurrentEvent())
            txt = self.input.getText()
            if not txt:
                return
            new_value = float(txt)
            new_value = self.processValue(new_value)
            self.setControlPos(new_value)
            self.setValue(new_value)
        else:
            Control.onKeyPress(self, sender, keycode, modifiers)

Factory.registerClass('pyjamas.ui.InputControl', InputControl)


class HorizontalDemoSlider(VerticalDemoSlider):
    def __init__(self, min_value, max_value, start_value=None, step=None,
                       **kwargs):

        VerticalDemoSlider.__init__(self, min_value, max_value, start_value,
                                    **kwargs)
        DOM.setStyleAttribute(self.handle, "width", "10px")
        DOM.setStyleAttribute(self.handle, "height", "100%")                                
    def moveControl(self, mouse_x, mouse_y):

        handle_width = DOM.getIntAttribute(self.handle, "offsetWidth")
        widget_width = self.getOffsetWidth()
        length_range = widget_width - 10 # handle width is hard-coded
        relative_x = mouse_x - (handle_width / 2)
        if relative_x < 0:
            relative_x = 0
        if relative_x >= length_range:
            relative_x = length_range

        val_diff = self.max_value - self.min_value
        new_value = ((val_diff * relative_x) / length_range) + self.min_value
        new_value = self.processValue(new_value)

        self.setControlPos(new_value)
        self.setValue(new_value)
    def setControlPos(self, value):

        widget_width = self.getOffsetWidth()
        length_range = widget_width - 10 # handle width is hard-coded
        val_diff = self.max_value - self.min_value
        relative_x = length_range * (value - self.min_value) / val_diff

        # limit the position to be in the widget!
        if relative_x < 0:
            relative_x = 0
        if relative_x >= length_range:
            relative_x = length_range

        # move the handle
        DOM.setStyleAttribute(self.handle, "left", "%dpx" % relative_x) 
        DOM.setStyleAttribute(self.handle, "position", "absolute")

Factory.registerClass('pyjamas.ui.HorizontalDemoSlider', HorizontalDemoSlider)


class HorizontalDemoSlider2(HorizontalDemoSlider):
    def __init__(self, min_value, max_value, start_value=None, **kwargs):

        HorizontalDemoSlider.__init__(self, min_value, max_value, start_value,
                                    **kwargs)
        self.addKeyboardListener(self)
        self.drag_enabled = True

Factory.registerClass('pyjamas.ui.HorizontalDemoSlider2', HorizontalDemoSlider2)


class AreaDemoSlider(DControl):
    def __init__(self, (min_value_x, min_value_y),
                       (max_value_x, max_value_y),
                        start_value=None, step=None,
                       **kwargs):

        if not kwargs.has_key("StyleName"):
            kwargs['StyleName'] = "gwt-VerticalSlider"

        if kwargs.has_key('Element'):
            # XXX FIXME: Focus.createFocusable is here for a reason...
            element = kwargs.pop('Element')
        else:
            element = Focus.createFocusable()
        DOM.setStyleAttribute(element, "position", "relative")
        DOM.setStyleAttribute(element, "overflow", "hidden")

        self.handle = DOM.createDiv()
        DOM.appendChild(element, self.handle)

        DOM.setStyleAttribute(self.handle, "border", "1px")
        DOM.setStyleAttribute(self.handle, "width", "100%")
        DOM.setStyleAttribute(self.handle, "height", "10px")
        DOM.setStyleAttribute(self.handle, "backgroundColor", "#808080")

        # must use DControl; otherwise, this init is = Vertical init,
        # plus a change in the handle style
        # this should be refactored, so that the AreaDemoSlider
        # can be built on VerticalDemaoSlider    
        DControl.__init__(self, element, (min_value_x, min_value_y),
                                         (max_value_x, max_value_y),
                               start_value, step,
                               **kwargs)

        self.addClickListener(self)
        self.addFocusListener(self)
        self.addMouseListener(self)

        #Redefine VDS's styles for handle
        DOM.setStyleAttribute(self.handle, "width", "10px")
        DOM.setStyleAttribute(self.handle, "height", "10px")                                
    def setValue(self, (new_value_x,new_value_y), notify=1):

        old_value_x = self.value_x
        self.value_x = new_value_x

        old_value_y = self.value_y
        self.value_y = new_value_y    

        if not notify:
            return

        for listener in self.valuechange_listeners:
            # how to handle this? ???
            listener.onControlValueChanged(self, (old_value_x, old_value_y),
                                                 (new_value_x, new_value_y))

    def onFocus(self, sender):
        self.addStyleName("gwt-VerticalSlider-focussed")

    def onLostFocus(self, sender):
        self.removeStyleName("gwt-VerticalSlider-focussed")
        self.dragging = False
        DOM.releaseCapture(self.getElement())
    def moveControl(self, mouse_x, mouse_y):

        handle_height = DOM.getIntAttribute(self.handle, "offsetHeight")
        widget_height = self.getOffsetHeight()
        height_range = widget_height - 10 # handle height is hard-coded
        relative_y = mouse_y - (handle_height / 2)
        if relative_y < 0:
            relative_y = 0
        if relative_y >= height_range:
            relative_y = height_range

        # turn round (bottom to top) for x
        relative_y = height_range - relative_y

        handle_width = DOM.getIntAttribute(self.handle, "offsetWidth")
        widget_width = self.getOffsetWidth()
        length_range = widget_width - 10 # handle width is hard-coded
        relative_x = mouse_x - (handle_width / 2)
        if relative_x < 0:
            relative_x = 0
        if relative_x >= length_range:
            relative_x = length_range

        val_diff_x = self.max_value_x - self.min_value_x
        new_value_x = ((val_diff_x * relative_x) / length_range) + \
                      self.min_value_x

        val_diff_y = self.max_value_y - self.min_value_y
        new_value_y = ((val_diff_y * relative_y) / height_range) + \
                      self.min_value_y

        new_value_x, new_value_y = self.processValue((new_value_x, new_value_y))    
        self.setControlPos((new_value_x, new_value_y))
        self.setValue((new_value_x, new_value_y))

    def setControlPos(self, (value_x, value_y)):

        widget_width = self.getOffsetWidth()
        length_range = widget_width - 10 # handle width is hard-coded
        val_diff_x = self.max_value_x - self.min_value_x
        relative_x = length_range * (value_x - self.min_value_x) / val_diff_x

        # limit the position to be in the widget!
        if relative_x < 0:
            relative_x = 0
        if relative_x >= length_range:
            relative_x = length_range

        widget_height = self.getOffsetHeight()
        height_range = widget_height - 10 # handle height is hard-coded
        val_diff_y = self.max_value_y - self.min_value_y
        relative_y = height_range * (value_y - self.min_value_y) / val_diff_y

        # limit the position to be in the widget!
        if relative_y < 0:
            relative_y = 0
        if relative_y >= height_range:
            relative_y = height_range

        relative_y = height_range - relative_y # turn round (bottom to top)

        # move the handle
        DOM.setStyleAttribute(self.handle, "top", "%dpx" % relative_y)    
        DOM.setStyleAttribute(self.handle, "left", "%dpx" % relative_x) 
        DOM.setStyleAttribute(self.handle, "position", "absolute")

Factory.registerClass('pyjamas.ui.AreaDemoSlider', AreaDemoSlider)


class AreaDemoSlider2(AreaDemoSlider):
    def __init__(self, (min_value_x, min_value_y),
                       (max_value_x, max_value_y), start_value=None, **kwargs):

        AreaDemoSlider.__init__(self, (min_value_x, min_value_y),
                                     (max_value_x, max_value_y), start_value,
                                    **kwargs)
        self.addKeyboardListener(self)
        self.drag_enabled = True

Factory.registerClass('pyjamas.ui.AreaDemoSlider2', AreaDemoSlider2)


