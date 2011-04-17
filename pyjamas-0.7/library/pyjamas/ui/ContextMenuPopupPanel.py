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
from PopupPanel import PopupPanel

class ContextMenuPopupPanel(PopupPanel):
    def __init__(self, item, **kwargs):
        self.item = item
        kwargs['Widget'] = item
        PopupPanel.__init__(self, True, **kwargs)

    def showAt(self, x, y):

        self.setPopupPosition(x, y)
        self.item.onShow()
        self.show()

    def onEventPreview(self, event):
        type = DOM.eventGetType(event)
        if type == "click":
            target = DOM.eventGetTarget(event)
            parentMenuElement = self.item.getElement()
            if DOM.isOrHasChild(parentMenuElement, target):
                if self.item.onBrowserEvent(event):
                    self.hide()
                return True

        return PopupPanel.onEventPreview(self, event)

Factory.registerClass('pyjamas.ui.ContextMenuPopupPanel', ContextMenuPopupPanel)

