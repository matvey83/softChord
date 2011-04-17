# Copyright 2006 James Tauber and contributors
# Copyright 2009 Luke Kenneth Casson Leighton
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

class HasHorizontalAlignment:
    ALIGN_LEFT = "left"
    ALIGN_CENTER = "center"
    ALIGN_RIGHT = "right"

class HasVerticalAlignment:
    ALIGN_TOP = "top"
    ALIGN_MIDDLE = "middle"
    ALIGN_BOTTOM = "bottom"

class HasAlignment:
    ALIGN_BOTTOM = "bottom"
    ALIGN_MIDDLE = "middle"
    ALIGN_TOP = "top"
    ALIGN_CENTER = "center"
    ALIGN_LEFT = "left"
    ALIGN_RIGHT = "right"

class Applier(object):
             
    def __init__(self, **kwargs):
        """ use this to apply properties as a dictionary, e.g.
                x = klass(..., StyleName='class-name')
            will do:
                x = klass(...)
                x.setStyleName('class-name')

            and:
                x = klass(..., Size=("100%", "20px"), Visible=False)
            will do:
                x = klass(...)
                x.setSize("100%", "20px")
                x.setVisible(False)
        """
        if kwargs:
            k = kwargs.keys()
            l = len(k)
            i = -1
            while i < l-1:
                i += 1
                prop = k[i]
                fn = getattr(self, "set%s" % prop, None)
                if fn:
                    args = kwargs[prop]
                    if isinstance(args, tuple):
                        fn(*args)
                    else:
                        fn(args)
class InnerHTML(object):

    def getHTML(self):
        return DOM.getInnerHTML(self.getElement())

    def setHTML(self, html):
        DOM.setInnerHTML(self.getElement(), html)

class InnerText(object):

    def setText(self, text):
        DOM.setInnerText(self.getElement(), text)

    def getText(self):
        return DOM.getInnerText(self.getElement())

