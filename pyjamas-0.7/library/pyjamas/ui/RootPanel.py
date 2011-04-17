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
import sys
from __pyjamas__ import doc
from pyjamas import Factory

from pyjamas import DOM
from pyjamas import Window

from AbsolutePanel import AbsolutePanel

rootPanels = {}
class RootPanelManager(object):

    def onWindowClosed(self):
        global rootPanels
        for panel in rootPanels.itervalues():
            panel.onDetach()

    def onWindowClosing(self):
        return None

def get(id=None):
    """

    """
    if rootPanels.has_key(id):
        return rootPanels[id]

    element = None
    if id:
        element = DOM.getElementById(id)
        if not element:
            return None

    return manageRootPanel(RootPanelCls(element), id)

def manageRootPanel(panel, id=None):

    if len(rootPanels) < 1:
        panelManager = RootPanelManager()
        Window.addWindowCloseListener(panelManager)

    rootPanels[id] = panel
    return panel

class RootPanelCls(AbsolutePanel):
    def __init__(self, Element=None, **kwargs):
        if Element:
            kwargs['Element'] = Element
        AbsolutePanel.__init__(self, **kwargs)
        if Element is None:
            # avoid having CSS styles position:relative and hidden set on body
            Element = self.getBodyElement()
            self.setElement(Element)
        self.onAttach()

    def getBodyElement(self):
        return doc().body

Factory.registerClass('pyjamas.ui.RootPanelCls', RootPanelCls)

def RootPanel(id=None):
    return get(id)

