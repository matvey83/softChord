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

from ButtonBase import ButtonBase

class Button(ButtonBase):

    def __init__(self, html=None, listener=None, **kwargs):
        """
        Create a new button widget.

        @param html: Html content (e.g. the button label); see setHTML()
        @param listener: A new click listener; see addClickListener()

        """
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-Button"
        if html: kwargs['HTML'] = html
        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createButton()
        ButtonBase.__init__(self, element, **kwargs)
        self.adjustType(self.getElement())
        if listener:
            self.addClickListener(listener)

    def adjustType(self, button):
        if button.type == 'submit':
            try:
                DOM.setAttribute(button, "type", "button")
            except:
                pass

    def click(self):
        """
        Simulate a button click.
        """
        self.getElement().click()

Factory.registerClass('pyjamas.ui.Button', Button)

