# Copyright Pyjamas Team
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http:/www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import sys

from pyjamas    import DOM
from pyjamas import Factory
from pyjamas.ui import Event
from ButtonBase import ButtonBase
from pyjamas.ui import Focus
from UIObject import UIObject

"""
Custom Button is a base button class with built in support for a set number
of button faces.

Each face has its own style modifier. For example, the state for down and
hovering is assigned the CSS modifier down-hovering. So, if the
button's overall style name is gwt-PushButton then when showing the
down-hovering face, the button's style is 
gwt-PushButton-down-hovering. The overall style name can be used to
change the style of the button irrespective of the current face.

Each button face can be assigned is own image, text, or html contents. If no
content is defined for a face, then the face will use the contents of another
face. For example, if down-hovering does not have defined
contents, it will use the contents defined by the down face.

The supported faces are defined below:

CSS          | Getter method       | description of face                       | delegateTo
-------------+---------------------+-------------------------------------------+---------
up           |getUpFace()          |face shown when button is up               |none
down         |getDownFace()        |face shown when button is down             | up
up-hovering  |getUpHoveringFace()  |face shown when button is up and hovering  | up
up-disabled  |getUpDisabledFace()  |face shown when button is up and disabled  | up
down-hovering|getDownHoveringFace()|face shown when button is down and hovering|down
down-disabled|getDownDisabledFace()|face shown when button is down and disabled|down
"""

class Face:
    STYLENAME_HTML_FACE = "html-face"
    
    def __init__(self, button, delegateTo = None):
        """
        Constructor for Face. Creates a face that delegates to
        the supplied face.
    
        @param delegateTo default content provider
        """
        self.button = button
        self.delegateTo = delegateTo
        self.face = None # TODO it is likely required. Im beginner in java/gwt source.
        self.id   = None # TODO
        self.name = "fazom" # TODO
    
    def getName(self): # FIXME
        """Returns with a known face's name"""
        return self.name
    
    def getFaceID(self): # FIXME
        """Returns with the face's id"""
        return self.id
    
    def setName(self, name): # FIXME
        """Sets the face's name"""
        self.name = name
        return
    
    def setFaceID(self, face_id): # FIXME
        """Sets the face's id"""
        self.id = face_id
        return
    
    def getHTML(self):
        """Gets the face's contents as html."""
        return DOM.getInnerHTML(self.getFace())
    
    
    def getText(self):
        """Gets the face's contents as text."""
        return DOM.getInnerText(self.getFace())
    
    
    def setHTML(self, html):
        """Set the face's contents as html."""
        self.face = DOM.createDiv()
        UIObject.setStyleName(self.button, self.face, self.STYLENAME_HTML_FACE, True)
        DOM.setInnerHTML(self.face, html)
        self.button.updateButtonFace()
    
    
    def setImage(self, image):
        """
        Set the face's contents as an image.
        @param image image to set as face contents
        """
        self.face = image.getElement()
        self.button.updateButtonFace()
    
    
    def setText(self, text):
        """
        Sets the face's contents as text.
        @param text text to set as face's contents
        """
        self.face = DOM.createDiv()
        UIObject.setStyleName(self.button, self.face, self.STYLENAME_HTML_FACE, True)
        DOM.setInnerText(self.face, text)
        self.button.updateButtonFace()
        
    
    def toString(self):
        return self.getName()
    
    def getFace(self):
        """Gets the contents associated with this face."""
        if self.face is None:
            if self.delegateTo is None:
                # provide a default face as none was supplied.
                self.face = DOM.createDiv()
                return self.face
            else:
                return self.delegateTo.getFace()
            
        else:
            return self.face
    
    
    

class CustomButton (ButtonBase):
    """
    Represents a button's face. Each face is associated with its own style
    modifier and, optionally, its own contents html, text, or image.
    """
            
    STYLENAME_DEFAULT  = "gwt-CustomButton"
    DOWN_ATTRIBUTE     = 1                  # Pressed Attribute bit.
    HOVERING_ATTRIBUTE = 2                  # Hovering Attribute bit.
    DISABLED_ATTRIBUTE = 4                  # Disabled Attribute bit.
    UP                 = 0                  # ID for up face.
    DOWN               = DOWN_ATTRIBUTE     # 1 ID for down face.
    UP_HOVERING        = HOVERING_ATTRIBUTE # 2 ID for upHovering face.
    DOWN_HOVERING = DOWN_ATTRIBUTE | HOVERING_ATTRIBUTE # 3 ID for downHovering face.
    UP_DISABLED   = DISABLED_ATTRIBUTE        # 4 ID for upDisabled face.
    DOWN_DISABLED = DOWN | DISABLED_ATTRIBUTE # 5 ID for downDisabled face.
    
    
    
    """ Calling possibilities:
    def __init__(self, upImage):
    def __init__(self, upImage, listener):
    def __init__(self, upImage, downImage):
    def __init__(self, upImage, downImage, listener):
    def __init__(self, upText):
    def __init__(self, upText, listener):
    def __init__(self, upText, downText):
    def __init__(self, upText, downText, listener):
    def __init__(self):


    TODO: I do not know how to handle the following cases:
    def __init__(self, upImage, listener):
    def __init__(self, upText, listener):
    
    So how can I make difference between listener and downImage/downText ?
    """
    
    def __init__(self, upImageText = None, downImageText=None, listener = None,
                       **kwargs):
        """Constructor for CustomButton."""
        
        if not kwargs.has_key('StyleName'): kwargs['StyleName']=self.STYLENAME_DEFAULT
        if kwargs.has_key('Element'):
            # XXX FIXME: createFocusable is used for a reason...
            element = kwargs.pop('Element')
        else:
            element = Focus.createFocusable()
        ButtonBase.__init__(self, element, **kwargs)

        self.curFace      = None # The button's current face.
        self.curFaceElement = None # No "undefined" anymore
        self.up           = None # Face for up.
        self.down         = None # Face for down.
        self.downHovering = None # Face for downHover.
        self.upHovering   = None # Face for upHover.
        self.upDisabled   = None # Face for upDisabled.
        self.downDisabled = None # Face for downDisabled.
        self.isCapturing = False # If True, this widget is capturing with 
                                 # the mouse held down.
        self.isFocusing  = False # If True, this widget has focus with the space bar down.
        self.allowClick  = False # Used to decide whether to allow clicks to 
                                 # propagate up to the superclass or container elements.
    
        self.setUpFace(self.createFace(None, "up", self.UP))
        #self.getUpFace().setText("Not initialized yet:)")
        #self.setCurrentFace(self.getUpFace())

        # Add a11y role "button"
        # XXX: TODO Accessibility
    
        # TODO: pyjslib.isinstance
        if downImageText is None and listener is None:
            listener = upImageText
            upImageText = None

        if upImageText and isinstance(upImageText, str):
           upText = upImageText
           upImage = None
        else:
           upImage = upImageText
           upText = None

        if downImageText and isinstance(downImageText, str):
           downText = downImageText
           downImage = None
        else:
           downImage = downImageText
           downText = None

        #self.getUpFace().setText("Just a test")
        if upImage: self.getUpFace().setImage(upImage)
        if upText: self.getUpFace().setText(upText)
        if downImage: self.getDownFace().setImage(downImage)
        if downText: self.getDownFace().setText(downText)
        
        # set the face DOWN
        #self.setCurrentFace(self.getDownFace())
        
        # set the face UP
        #self.setCurrentFace(self.getUpFace())
    
        self.sinkEvents(Event.ONCLICK | Event.MOUSEEVENTS | Event.FOCUSEVENTS
                        | Event.KEYEVENTS)
        if listener: self.addClickListener(listener)
    
    def updateButtonFace(self):
        if self.curFace is not None and \
           self.curFace.getFace() == self.getFace():
            self.setCurrentFaceElement(self.face)
    
    
    def getDownDisabledFace(self):
        """Gets the downDisabled face of the button."""
        if self.downDisabled is None:
            self.setDownDisabledFace(self.createFace(self.getDownFace(), 
                                     "down-disabled", self.DOWN_DISABLED))
        
        return self.downDisabled
    
    
    def getDownFace(self):
        """Gets the down face of the button."""
        if self.down is None:
            self.setDownFace(self.createFace(self.getUpFace(), 
                             "down", self.DOWN))
        return self.down
    
    
    def getDownHoveringFace(self):
        """Gets the downHovering face of the button."""
        if self.downHovering is None:
            self.setDownHoveringFace(self.createFace(self.getDownFace(), 
                                "down-hovering", self.DOWN_HOVERING))
        return self.downHovering
    
    
    def getHTML(self):
        """Gets the current face's html."""
        return self.getCurrentFace().getHTML()
    
    
    def getTabIndex(self):
        return Focus.getTabIndex(self.getElement())
    
    
    def getText(self):
        """Gets the current face's text."""
        return self.getCurrentFace().getText()
    
    
    def getUpDisabledFace(self):
        """Gets the upDisabled face of the button."""
        if self.upDisabled is None:
            self.setUpDisabledFace(self.createFace(self.getUpFace(), 
                                   "up-disabled", self.UP_DISABLED))
        return self.upDisabled
    
    
    def getUpFace(self):
        """Gets the up face of the button."""
        return self.up # self.up must be always initialized
    
    
    def getUpHoveringFace(self):
        """Gets the upHovering face of the button."""
        if self.upHovering is None:
            self.setUpHoveringFace(self.createFace(self.getUpFace(), 
                                   "up-hovering", self.UP_HOVERING))
        return self.upHovering
    

    def onBrowserEvent(self, event):
        # Should not act on button if disabled.
        if not self.isEnabled():
            # This can happen when events are bubbled up from
            # non-disabled children
            return
        
        event_type = DOM.eventGetType(event)
        
        if event_type == "click":
            # If clicks are currently disallowed, keep it from bubbling or
            # being passed to the superclass.
            if not self.allowClick:
                DOM.eventStopPropagation(event)
                return
            
        elif event_type == "mousedown":
            if DOM.eventGetButton(event) == Event.BUTTON_LEFT:
                self.setFocus(True)
                self.onClickStart()
                DOM.setCapture(self.getElement())
                self.isCapturing = True
                # Prevent dragging (on some browsers)
                DOM.eventPreventDefault(event)
            
        elif event_type == "mouseup":
            if self.isCapturing:
                self.isCapturing = False
                DOM.releaseCapture(self.getElement())
                if self.isHovering()  and  \
                   DOM.eventGetButton(event) == Event.BUTTON_LEFT:
                    self.onClick()
                
            
        elif event_type == "mousemove":
            if self.isCapturing:
                # Prevent dragging (on other browsers)
                DOM.eventPreventDefault(event)
            
        elif event_type == "mouseout":
            to = DOM.eventGetToElement(event)
            if (DOM.isOrHasChild(self.getElement(), DOM.eventGetTarget(event))
               and (to is None or not DOM.isOrHasChild(self.getElement(), to))):
                if self.isCapturing:
                    self.onClickCancel()
                self.setHovering(False)
            
        elif event_type == "mouseover":
            if DOM.isOrHasChild(self.getElement(), DOM.eventGetTarget(event)):
                self.setHovering(True)
                if self.isCapturing:
                    self.onClickStart()
            
        elif event_type == "blur":
            if self.isFocusing:
                self.isFocusing = False
                self.onClickCancel()
            
        elif event_type == "losecapture":
            if self.isCapturing:
                self.isCapturing = False
                self.onClickCancel()
            
        ButtonBase.onBrowserEvent(self, event)
        
        # Synthesize clicks based on keyboard events AFTER the normal
        # key handling.
        if (DOM.eventGetTypeInt(event) & Event.KEYEVENTS) != 0:
            keyCode = DOM.eventGetKeyCode(event)
            if event_type == "keydown":
                if keyCode == ' ':
                    self.isFocusing = True
                    self.onClickStart()
                
            elif event_type == "keyup":
                if self.isFocusing  and  keyCode == ' ':
                    self.isFocusing = False
                    self.onClick()
                
            elif event_type == "keypress":
                if keyCode == '\n'  or  keyCode == '\r':
                    self.onClickStart()
                    self.onClick()
                
    

    def setAccessKey(self, key):
        # TODO: accessibility 
        # Focus.setAccessKey(self.getElement(), key)
        pass
    
    def setEnabled(self, enabled):
        """Sets whether this button is enabled."""
        if self.isEnabled() != enabled:
            self.toggleDisabled()
            ButtonBase.setEnabled(self, enabled)
            if not enabled:
                self.cleanupCaptureState()
                # XXX - TODO: Accessibility
            else:
                self.setAriaPressed(self.getCurrentFace())
        

    def setFocus(self, focused):
        if focused:
            Focus.focus(self.getElement())
        else:
            Focus.blur(self.getElement())
        
    
    def setHTML(self, html):
        """Sets the current face's html."""
        self.getCurrentFace().setHTML(html)
    
    
    def setTabIndex(self, index):
        Focus.setTabIndex(self.getElement(), index)
    
    
    def setText(self, text):
        """Sets the current face's text."""
        self.getCurrentFace().setText(text)
    
    
    def isDown(self):
        """Is this button down?"""
        # 0->0, 1->1, 2->0, 3->1, 4->0, 5->1
        return (self.DOWN_ATTRIBUTE & self.getCurrentFace().getFaceID()) > 0
    
    
    def onAttach(self):
        """
        Overridden on attach to ensure that a button face has been chosen before
        the button is displayed.
        """
        self.finishSetup()
        ButtonBase.onAttach(self)
    
    
    def onClick(self, sender=None):
        """
        Called when the user finishes clicking on this button.
        The default behavior is to fire the click event to
        listeners. Subclasses that override onClickStart() should
        override this method to restore the normal widget display.
        """
        # Allow the click we're about to synthesize to pass through to the
        # superclass and containing elements. Element.dispatchEvent() is
        # synchronous, so we simply set and clear the flag within this method.
        self.allowClick = True
        
        # Mouse coordinates are not always available (e.g., when the click is
        # caused by a keyboard event).
        evt = None # we NEED to initialize evt, to be in the same namespace 
                   # as the evt *inside* of JS block

        # We disallow setting the button here, because IE doesn't provide the
        # button property for click events.
        
        # there is a good explanation about all the arguments of initMouseEvent
        # at: https://developer.mozilla.org/En/DOM:event.initMouseEvent
        
        DOM.buttonClick(self.getElement())
        self.allowClick = False
    
    
    def onClickCancel(self):
        """
        Called when the user aborts a click in progress; for example, by 
        dragging the mouse outside of the button before releasing the mouse 
        button. Subclasses that override onClickStart() should override this
        method to restore the normal widget display.
        """
        pass
    
    
    def onClickStart(self):
        """
        Called when the user begins to click on this button. Subclasses may
        override this method to display the start of the click visually; such
        subclasses should also override onClick() and onClickCancel() to
        restore normal visual state. Each onClickStart will eventually be
        followed by either onClick or onClickCancel, depending on whether
        the click is completed.
        """
        pass
    
    
    def onDetach(self):
        ButtonBase.onDetach(self)
        self.cleanupCaptureState()
    
    
    def setDown(self, down):
        """Sets whether this button is down."""
        if down != self.isDown():
            self.toggleDown()
        
    
    def finishSetup(self): #default
        """Common setup between constructors."""
        if self.curFace is None:
            self.setCurrentFace(self.getUpFace())
        
    
    
    def fireClickListeners(self, nativeEvent):
        # TODO(ecc) Once event triggering is committed, should fire a
        # click event instead.
        self.fireEvent(ClickEvent()) # TODO: ???
        
    def fireEvent(self):
        # TODO: there is no standard mechanism in pyjamas?
        pass
    
    
    def getCurrentFace(self):
        """
        Gets the current face of the button.
        Implementation note: Package so we can use it when testing the
        button.
        """
        self.finishSetup()
        return self.curFace
    
    
    def isHovering(self):
        """Is the mouse hovering over this button? Returns True"""
        return (self.HOVERING_ATTRIBUTE & self.getCurrentFace().getFaceID()) > 0
    
    
    def setHovering(self, hovering):
        """Sets whether this button is hovering."""
        if hovering != self.isHovering(): # TODO
            self.toggleHover()
        
    
    def toggleDown(self):
        """Toggle the up/down attribute."""
        newFaceID = self.getCurrentFace().getFaceID() ^ self.DOWN_ATTRIBUTE
        self.setCurrentFaceFromID(newFaceID) # newFaceId: 0,1,2,3,4,5

    
    def cleanupCaptureState(self):
        """
        Resets internal state if this button can no longer service events.
        This can occur when the widget becomes detached or disabled.
        """
        if self.isCapturing or self.isFocusing:
            DOM.releaseCapture(self.getElement())
            self.isCapturing = False
            self.isFocusing = False
            self.onClickCancel()
    
    
        
    def createFace(self, delegateTo, name, faceID):
        # TODO: name and faceID
        # TODO: maybe no need to break it into this pieces
        face = Face(self, delegateTo) 
        face.setName(name)
        face.setFaceID(faceID)
        return face


    def getFaceFromID(self, face_id):
        if (face_id == self.DOWN):
            return self.getDownFace()
        elif(face_id == self.UP):
            return self.getUpFace()
        elif (face_id == self.DOWN_HOVERING):
            return self.getDownHoveringFace()
        elif (face_id == self.UP_HOVERING):
            return self.getUpHoveringFace()
        elif (face_id == self.UP_DISABLED):
            return self.getUpDisabledFace()
        elif (face_id == self.DOWN_DISABLED):
            return self.getDownDisabledFace()
        else:
            print id, " is not a known face id."

            # TODO ???
    
    def setAriaPressed(self, newFace):
        pressed = (newFace.getFaceID() & self.DOWN_ATTRIBUTE) == 1
        # XXX: TODO Accessibility
        


    def setCurrentFace(self, newFace):
        """Implementation note: default access for testing."""
        if self.curFace != newFace:
            if self.curFace is not None:
                self.removeStyleDependentName(self.curFace.getName())
            
            self.curFace = newFace
            self.setCurrentFaceElement(newFace.getFace());
            self.addStyleDependentName(self.curFace.getName())
            
            if self.isEnabled:
                self.setAriaPressed(newFace)    
            #self.updateButtonFace() # TODO: should we comment out?
            self.style_name = self.getStyleName()

    
    def setCurrentFaceFromID(self, faceID):
        """Sets the current face based on the faceID."""
        # this is a new method compared by gwt. Likely to be removed.
        newFace = self.getFaceFromID(faceID)
        self.setCurrentFace(newFace)
    
    
    def setCurrentFaceElement(self, newFaceElement):
        # XXX: TODO
        if self.curFaceElement != newFaceElement:
            if self.curFaceElement is not None:
                DOM.removeChild(self.getElement(), self.curFaceElement)
            
            self.curFaceElement = newFaceElement
            DOM.appendChild(self.getElement(), self.curFaceElement)
        
    
    def setDownDisabledFace(self, downDisabled):
        """Sets the downDisabled face of the button."""
        self.downDisabled = downDisabled
    
    
    def setDownFace(self, down):
        """Sets the down face of the button."""
        self.down = down
    
    
    def setDownHoveringFace(self, downHovering):
        """Sets the downHovering face of the button."""    
        self.downHovering = downHovering
    
    
    def setUpDisabledFace(self, upDisabled):
        """Sets the upDisabled face of the button."""
        self.upDisabled = upDisabled
    
    
    def setUpFace(self, up):
        """Sets the up face of the button."""
        self.up = up
    
    
    def setUpHoveringFace(self, upHovering):
        """Sets the upHovering face of the button."""
        self.upHovering = upHovering
    
    
    def toggleDisabled(self):
        """Toggle the disabled attribute."""
        # Toggle disabled.
        newFaceID = self.getCurrentFace().getFaceID() ^ self.DISABLED_ATTRIBUTE
        
        # Remove hovering.
        newFaceID &= ~self.HOVERING_ATTRIBUTE
        
        # Sets the current face.
        self.setCurrentFaceFromID(newFaceID)
    
    
    def toggleHover(self):
        """Toggle the hovering attribute."""
    
        # Toggle hovering.
        newFaceID = self.getCurrentFace().getFaceID() ^ self.HOVERING_ATTRIBUTE
        
        # Remove disabled.
        newFaceID &= ~self.DISABLED_ATTRIBUTE
        self.setCurrentFaceFromID(newFaceID)

Factory.registerClass('pyjamas.ui.CustomButton', CustomButton)

