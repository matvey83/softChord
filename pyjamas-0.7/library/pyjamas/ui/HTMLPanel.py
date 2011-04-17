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
from pyjamas.ui import InnerHTML

from ComplexPanel import ComplexPanel

HTMLPanel_sUid = 0

def getElementsByTagName(element, tagname):
    try:
        element_tagname = element.nodeName # DOM.getAttribute(element, "nodeName")
        element_tagname = str(element_tagname).lower()
    except:
        element_tagname = None
    if element_tagname is not None and element_tagname == tagname:
        return [element]

    res = []
    child = DOM.getFirstChild(element)
    while child is not None:
        for el in getElementsByTagName(child, tagname):
            res.append(el)
        child = DOM.getNextSibling(child)

    return res

def getElementById(element, id):
    try:
        element_id = DOM.getAttribute(element, "id")
    except:
        element_id = None
    if element_id is not None and element_id == id:
        return element

    child = DOM.getFirstChild(element)
    while child is not None:
        ret = getElementById(child, id)
        if ret is not None:
            return ret
        child = DOM.getNextSibling(child)

    return None


class HTMLPanel(ComplexPanel, InnerHTML):
    def __init__(self, html, **kwargs):
        # NOTE! don't set a default style on this panel, because the
        # HTML might expect to have one already.
        #if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-HTMLPanel"
        if html: kwargs['HTML'] = html
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createDiv()
        self.setElement(element)
        ComplexPanel.__init__(self, **kwargs)

    def add(self, widget, id):
        element = getElementById(self.getElement(), id)
        if element is None:
            # throw new NoSuchElementException()
            return
        ComplexPanel.add(self, widget, element)

    def findTags(self, tagname):
        return getElementsByTagName(self.getElement(), tagname)

    @staticmethod
    def createUniqueId():
        global HTMLPanel_sUid

        HTMLPanel_sUid += 1
        return "HTMLPanel_%d" % HTMLPanel_sUid

Factory.registerClass('pyjamas.ui.HTMLPanel', HTMLPanel)

