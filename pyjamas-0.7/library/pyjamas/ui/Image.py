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

from Widget import Widget
from pyjamas.ui import Event
from MouseListener import MouseHandler
from ClickListener import ClickHandler

prefetchImages = {}

class Image(Widget, MouseHandler, ClickHandler):
    def __init__(self, url="", **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-Image"
        if url: kwargs['Url'] = url

        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createImg()
        self.setElement(element)
        Widget.__init__(self, **kwargs)
        MouseHandler.__init__(self)
        ClickHandler.__init__(self)
        self.sinkEvents(Event.ONLOAD | Event.ONERROR)
        self.loadListeners = []

    def addLoadListener(self, listener):
        self.loadListeners.append(listener)

    def removeLoadListener(self, listener):
        self.loadListeners.remove(listener)

    def getUrl(self):
        return DOM.getAttribute(self.getElement(), "src")

    def onBrowserEvent(self, event):
        Widget.onBrowserEvent(self, event)
        type = DOM.eventGetType(event)
        if type == "load":
            for listener in self.loadListeners:
                listener.onLoad(self)
        elif type == "error":
            for listener in self.loadListeners:
                listener.onError(self)

    def prefetch(self, url):
        img = DOM.createImg()
        DOM.setElemAttribute(img, "src", url)
        prefetchImages[url] = img

    def setUrl(self, url):
        DOM.setElemAttribute(self.getElement(), "src", url)

Factory.registerClass('pyjamas.ui.Image', Image)

