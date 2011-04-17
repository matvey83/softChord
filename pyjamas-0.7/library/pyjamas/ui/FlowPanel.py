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

from ComplexPanel import ComplexPanel

class FlowPanel(ComplexPanel):
    def __init__(self, **kwargs):
        element = None
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        if element is None:
            element = DOM.createDiv()
        self.setElement(element)
        ComplexPanel.__init__(self, **kwargs)

    def add(self, w):
        ComplexPanel.add(self, w, self.getElement())

    def remove(self, index):
        if isinstance(index, int):
            index = self.getWidget(index)
        return ComplexPanel.remove(self, index)

Factory.registerClass('pyjamas.ui.FlowPanel', FlowPanel)

