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

from SimplePanel import SimplePanel

class CaptionPanel(SimplePanel):
    """
    A panel that wraps its contents in a border with a caption that appears in
    the upper left corner of the border. This is an implementation of the
    fieldset HTML element.
    """

    def __init__(self, caption, widget=None, **kwargs):
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createElement("fieldset")
        self.legend = DOM.createElement("legend")
        DOM.appendChild(element, self.legend)
        kwargs['Caption'] = caption
        if widget is not None:
            kwargs['Widget'] = widget
        SimplePanel.__init__(self, element, **kwargs)

    def getCaption(self):
        return self.caption

    def setCaption(self, caption):
        self.caption = caption
        if caption is not None and not caption == "":
            DOM.setInnerHTML(self.legend, caption)
            DOM.insertChild(self.getElement(), self.legend, 0)
        elif DOM.getParent(self.legend) is not None:
            DOM.removeChild(self.getElement(), self.legend)

Factory.registerClass('pyjamas.ui.CaptionPanel', CaptionPanel)

