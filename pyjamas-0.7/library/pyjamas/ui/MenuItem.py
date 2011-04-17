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

from UIObject import UIObject
from pyjamas.ui import Event
from pyjamas.ui import InnerHTML, InnerText

class MenuItem(UIObject, InnerHTML, InnerText):
    # also callable as:
    #   MenuItem(text, cmd)
    #   MenuItem(text, asHTML, cmd)
    #   MenuItem(text, subMenu)
    #   MenuItem(text, asHTML)
    def __init__(self, text, asHTML, subMenu=None, **kwargs):
        cmd = None
        if subMenu is None:
            if hasattr(asHTML, "execute"): # text, cmd
                cmd = asHTML
                asHTML = False
            elif hasattr(asHTML, "onShow"): # text, subMenu
                subMenu = asHTML
                asHTML = False
            # else: text, asHTML
        elif hasattr(subMenu, "execute"): # text, asHTML, cmd
            cmd = subMenu
            subMenu = None
        # else: text, asHTML, subMenu

        self.command = None
        self.parentMenu = None
        self.subMenu = None

        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createTD()
        self.setElement(element)

        kwargs['SelectionStyle'] = False
        if asHTML:
            kwargs['HTML'] = text
        else:
            kwargs['Text'] = text

        if cmd:
            kwargs['Command'] = cmd
        if subMenu:
            kwargs['SubMenu'] = subMenu

        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-MenuItem"

        UIObject.__init__(self, **kwargs)
        self.sinkEvents(Event.ONCLICK | Event.ONMOUSEOVER | Event.ONMOUSEOUT)

    def getCommand(self):
        return self.command

    def getParentMenu(self):
        return self.parentMenu

    def getSubMenu(self):
        return self.subMenu

    def setCommand(self, cmd):
        self.command = cmd

    def setSubMenu(self, subMenu):
        self.subMenu = subMenu

    def setParentMenu(self, parentMenu):
        self.parentMenu = parentMenu

    def setSelectionStyle(self, selected):
        if selected:
            self.addStyleName("gwt-MenuItem-selected")
        else:
            self.removeStyleName("gwt-MenuItem-selected")

Factory.registerClass('pyjamas.ui.MenuItem', MenuItem)

