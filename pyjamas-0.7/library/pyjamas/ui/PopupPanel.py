# Copyright 2006 James Tauber and contributors
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from pyjamas import DOM
from pyjamas import Factory
from __pyjamas__ import JS
from SimplePanel import SimplePanel
from RootPanel import RootPanel
from pyjamas.ui import MouseListener
from pyjamas.ui import KeyboardListener

class PopupPanel(SimplePanel):
    def __init__(self, autoHide=False, modal=True, rootpanel=None, **kwargs):

        self.popupListeners = []
        self.showing = False
        self.autoHide = autoHide
        self.modal = modal
        
        if rootpanel is None:
            rootpanel = RootPanel()

        self.rootpanel = rootpanel

        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = self.createElement()
        DOM.setStyleAttribute(element, "position", "absolute")

        SimplePanel.__init__(self, element, **kwargs)

    def addPopupListener(self, listener):
        self.popupListeners.append(listener)

    def getPopupLeft(self):
        return DOM.getIntAttribute(self.getElement(), "offsetLeft")

    def getPopupTop(self):
        return DOM.getIntAttribute(self.getElement(), "offsetTop")

    # PopupImpl.createElement
    def createElement(self):
        return DOM.createDiv()

    def hide(self, autoClosed=False):
        if not self.showing:
            return
        self.showing = False
        DOM.removeEventPreview(self)

        self.rootpanel.remove(self)
        self.onHideImpl(self.getElement())
        for listener in self.popupListeners:
            if hasattr(listener, 'onPopupClosed'): listener.onPopupClosed(self, autoClosed)
            else: listener(self, autoClosed)

    def isModal(self):
        return self.modal

    def _event_targets_popup(self, event):
        target = DOM.eventGetTarget(event)
        return target and DOM.isOrHasChild(self.getElement(), target)

    def onEventPreview(self, event):
        type = DOM.eventGetType(event)
        if type == "keydown":
            return (    self.onKeyDownPreview(
                            DOM.eventGetKeyCode(event),
                            KeyboardListener.getKeyboardModifiers(event)
                            )
                    and (not self.modal or self._event_targets_popup(event))
                   )
        elif type == "keyup":
            return (    self.onKeyUpPreview(
                            DOM.eventGetKeyCode(event),
                            KeyboardListener.getKeyboardModifiers(event)
                            )
                    and (not self.modal or self._event_targets_popup(event))
                   )
        elif type == "keypress":
            return (    self.onKeyPressPreview(
                            DOM.eventGetKeyCode(event),
                            KeyboardListener.getKeyboardModifiers(event)
                            )
                    and (not self.modal or self._event_targets_popup(event))
                   )
        elif (   type == "mousedown"
              or type == "blur"
             ):
            if DOM.getCaptureElement() is not None:
                return True
            if self.autoHide and not self._event_targets_popup(event):
                self.hide(True)
                return True
        elif (   type == "mouseup"
              or type == "click"
              or type == "mousemove"
              or type == "dblclick"
             ):
            if DOM.getCaptureElement() is not None:
                return True
        return not self.modal or self._event_targets_popup(event)

    def onKeyDownPreview(self, key, modifiers):
        return True

    def onKeyPressPreview(self, key, modifiers):
        return True

    def onKeyUpPreview(self, key, modifiers):
        return True

    # PopupImpl.onHide
    def onHideImpl(self, popup):
        pass

    # PopupImpl.onShow
    def onShowImpl(self, popup):
        pass

    def removePopupListener(self, listener):
        self.popupListeners.remove(listener)

    def setPopupPosition(self, left, top):
        if left < 0:
            left = 0
        if top < 0:
            top = 0

        # Account for the difference between absolute position and the
        # body's positioning context.
        left -= DOM.getBodyOffsetLeft()
        top -= DOM.getBodyOffsetTop()

        element = self.getElement()
        DOM.setStyleAttribute(element, "left", "%dpx" % left)
        DOM.setStyleAttribute(element, "top", "%dpx" % top)


    def show(self):
        if self.showing:
            return

        self.showing = True
        DOM.addEventPreview(self)

        self.rootpanel.add(self)
        self.onShowImpl(self.getElement())

Factory.registerClass('pyjamas.ui.PopupPanel', PopupPanel)

