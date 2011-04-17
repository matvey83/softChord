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
from __pyjamas__ import JS

def blur(elem):
    elem.blur()

def createFocusable():
    e = DOM.createDiv()
    e.tabIndex = 0
    return e

def focus(elem):
    elem.focus()

def getTabIndex(elem):
    return elem.tabIndex

def setAccessKey(elem, key):
    elem.accessKey = key

def setTabIndex(elem, index):
    elem.tabIndex = index


class FocusMixin:

    def getTabIndex(self):
        return getTabIndex(self.getElement())

    def setAccessKey(self, key):
        setAccessKey(self.getElement(), key)

    def setFocus(self, focused):
        if (focused):
            focus(self.getElement())
        else:
            blur(self.getElement())

    def setTabIndex(self, index):
        setTabIndex(self.getElement(), index)

    def isEnabled(self):
        try:
            return not DOM.getBooleanAttribute(self.getElement(), "disabled")
        except TypeError:
            return True
        except AttributeError:
            return True

    def setEnabled(self, enabled):
        DOM.setBooleanAttribute(self.getElement(), "disabled", not enabled)

    def isReadonly(self):
        try:
            return not DOM.getBooleanAttribute(self.getElement(), "readOnly")
        except TypeError:
            return True
        except AttributeError:
            return True
    
    def setReadonly(self, readonly):
        DOM.setBooleanAttribute(self.getElement(), "readOnly", readonly)

