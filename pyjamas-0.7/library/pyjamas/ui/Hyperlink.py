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
from pyjamas import History

from Widget import Widget
from pyjamas.ui import Event
from ClickListener import ClickHandler

class Hyperlink(Widget, ClickHandler):

    def __init__(self, text="", asHTML=False, targetHistoryToken="",
                       Element=None, **kwargs):

        self.targetHistoryToken = ""

        if not Element:
            Element = DOM.createDiv()
        self.anchorElem = DOM.createAnchor()
        self.setElement(Element)
        DOM.appendChild(self.getElement(), self.anchorElem)

        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-Hyperlink"
        if text:
            if asHTML:
                kwargs['HTML'] = text
            else:
                kwargs['Text'] = text
        if targetHistoryToken:
            kwargs['TargetHistoryToken'] = targetHistoryToken

        Widget.__init__(self, **kwargs)
        ClickHandler.__init__(self)

    def getHTML(self):
        return DOM.getInnerHTML(self.anchorElem)

    def getTargetHistoryToken(self):
        return self.targetHistoryToken

    def getText(self):
        return DOM.getInnerText(self.anchorElem)

    def onBrowserEvent(self, event):
        Widget.onBrowserEvent(self, event)
        if DOM.eventGetType(event) == "click":
            DOM.eventPreventDefault(event)
            History.newItem(self.targetHistoryToken)

    def setHTML(self, html):
        DOM.setInnerHTML(self.anchorElem, html)

    def setTargetHistoryToken(self, targetHistoryToken):
        self.targetHistoryToken = targetHistoryToken
        DOM.setAttribute(self.anchorElem, "href", "#" + targetHistoryToken)

    def setText(self, text):
        DOM.setInnerText(self.anchorElem, text)

Factory.registerClass('pyjamas.ui.Hyperlink', Hyperlink)

