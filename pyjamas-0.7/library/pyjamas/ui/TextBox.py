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

from TextBoxBase import TextBoxBase

class TextBox(TextBoxBase):
    def __init__(self, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-TextBox"
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createInputText()
        TextBoxBase.__init__(self, element, **kwargs)

    def getMaxLength(self):
        return DOM.getIntAttribute(self.getElement(), "maxLength")

    def getVisibleLength(self):
        return DOM.getIntAttribute(self.getElement(), "size")

    def setMaxLength(self, length):
        DOM.setIntAttribute(self.getElement(), "maxLength", length)

    def setVisibleLength(self, length):
        DOM.setIntAttribute(self.getElement(), "size", length)

Factory.registerClass('pyjamas.ui.TextBox', TextBox)

