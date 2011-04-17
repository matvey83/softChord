"""
* Copyright 2007 Google Inc.
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
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


from pyjamas import DOM

from pyjamas.ui import Event
from pyjamas.ui import Focus

"""*
* Base class for RichText platform implementations. The default version
* simply creates a text area with no rich text support.
*
* This is not currently used by any user-agent, but will provide a
* &lt;textarea&gt; fallback in the event a future browser fails to implement
* rich text editing.
"""
class RichTextAreaImpl:
    
    def __init__(self):
        self.elem = self.createElement()
    
    
    def getElement(self):
        return self.elem
    
    
    def getHTML(self):
        return DOM.getElementProperty(self.elem, "value")
    
    
    def getText(self):
        return DOM.getElementProperty(self.elem, "value")
    
    
    def initElement(self):
        onElementInitialized()
    
    
    def isBasicEditingSupported(self):
        return False
    
    
    def isExtendedEditingSupported(self):
        return False
    
    
    def setHTML(self, html):
        DOM.setElementProperty(self.elem, "value", html)
    
    
    def setText(self, text):
        DOM.setElementProperty(self.elem, "value", text)
    
    
    def uninitElement(self):
        pass
    
    
    def setFocus(self, focused):
        if (focused):
            Focus.focus(self.getElement())
        else:
            Focus.blur(self.getElement())

    def createElement(self):
        return DOM.createTextArea()
    
    
    def hookEvents(self):
        DOM.sinkEvents(self.elem, Event.MOUSEEVENTS | Event.KEYEVENTS | Event.ONCHANGE
        | Event.ONCLICK | Event.FOCUSEVENTS)
    
    
    def onElementInitialized(self):
        self.hookEvents()
    


