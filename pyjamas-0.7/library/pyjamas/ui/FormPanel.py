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
from __pyjamas__ import JS
from pyjamas import Factory
if sys.platform not in ['mozilla', 'ie6', 'opera', 'oldmoz', 'safari']:
    from __pyjamas__ import get_main_frame

from pyjamas import DOM
from __pyjamas__ import JS

from SimplePanel import SimplePanel
from pyjamas.ui import Event
from EventObject import EventObject

class FormSubmitEvent(EventObject):
    def __init__(self, source):
       EventObject.__init__(self, source)
       self.cancel = False # ?

    def isCancelled(self):
       return self.cancel

    def setCancelled(self, cancel):
       self.cancel = cancel

class FormSubmitCompleteEvent(EventObject):
    def __init__(self, source, results):
       EventObject.__init__(self, source)
       self.results = results
    def getResults(self):
       return self.results

FormPanel_formId = 0

class FormPanel(SimplePanel):
    ENCODING_MULTIPART = "multipart/form-data"
    ENCODING_URLENCODED = "application/x-www-form-urlencoded"
    METHOD_GET = "get"
    METHOD_POST = "post"

    def __init__(self, target = None, **kwargs):
        global FormPanel_formId

        if hasattr(target, "getName"):
            target = target.getName()

        if kwargs.has_key('Element'):
            element = kwargs.pop('Element')
        else:
            element = DOM.createForm()

        self.formHandlers = []
        self.iframe = None
        self.__formAction = None

        FormPanel_formId += 1
        formName = "FormPanel_" + str(FormPanel_formId)
        DOM.setAttribute(element, "target", formName)
        DOM.setInnerHTML(element, """<iframe name='%s' src="javascript:''">"""\
                                  % formName)
        self.iframe = DOM.getFirstChild(element)

        DOM.setIntStyleAttribute(self.iframe, "width", 0)
        DOM.setIntStyleAttribute(self.iframe, "height", 0)
        DOM.setIntStyleAttribute(self.iframe, "border", 0)

        if target is not None:
            kwargs['Target'] = target

        SimplePanel.__init__(self, element, **kwargs)

        try:
            self.sinkEvents(Event.ONLOAD)
        except:
            # MSHTML doesn't have form.onload,
            # it has onreadystatechange.
            pass

    def addFormHandler(self, handler):
        self.formHandlers.append(handler)

    def getAction(self):
        return DOM.getAttribute(self.getElement(), "action")

    # FormPanelImpl.getEncoding
    def getEncoding(self):
        elem = self.getElement()
        if hasattr(elem, 'enctype'):
            return elem.enctype
        return elem.encoding

    def getMethod(self):
        return DOM.getAttribute(self.getElement(), "method")

    def getTarget(self):
        return DOM.getAttribute(self.getElement(), "target")

    # FormPanelImpl.getTextContents
    def getTextContents(self, iframe):
        try:
            if not iframe.contentDocument:
                return None
            return DOM.getInnerHTML(iframe.contentDocument.body)
        except:
            return None

    def _onload(self, form, event, something):
        print form, event, something
        if not self.__formAction:
            return
        self._listener.onFrameLoad()

    def _onsubmit(self, form, event, something):
        print form, event, something
        try:
            event = get_main_frame().gobject_wrap(event) # webkit HACK!
            form = get_main_frame().gobject_wrap(form) # webkit HACK!
        except:
            pass

        if self.iframe:
            self.__formAction = form.action
        return self._listener.onFormSubmit()

    # FormPanelImpl.hookEvents
    def hookEvents(self, iframe, form, listener):
        # TODO: might have to fix this, use DOM.set_listener()
        self._listener = listener
        if iframe:
            wf = mf = get_main_frame()
            self._onload_listener = mf.addEventListener(iframe, "load",
                                                        self._onload)

        self._onsubmit_listener = mf.addEventListener(form, "onsubmit",
                                                    self._onsubmit)

    def onFormSubmit(self):
        event = FormSubmitEvent(self)
        for handler in self.formHandlers:
            handler.onSubmit(event)

        return not event.isCancelled()

    def onFrameLoad(self):
        event = FormSubmitCompleteEvent(self, self.getTextContents(self.iframe))
        for handler in self.formHandlers:
            handler.onSubmitComplete(event)

    def removeFormHandler(self, handler):
        self.formHandlers.remove(handler)

    def setAction(self, url):
        DOM.setAttribute(self.getElement(), "action", url)

    # FormPanelImpl.setEncoding
    def setEncoding(self, encodingType):
        form = self.getElement()
        if hasattr(form, 'enctype'):
            form.enctype = encodingType
        form.encoding = encodingType

    def setMethod(self, method):
        DOM.setAttribute(self.getElement(), "method", method)

    def submit(self):
        event = FormSubmitEvent(self)
        for handler in self.formHandlers:
            handler.onSubmit(event)

        if event.isCancelled():
            return

        self.submitImpl(self.getElement(), self.iframe)

    # FormPanelImpl.submit
    def submitImpl(self, form, iframe):
        if iframe:
            self.__formAction = form.action
        form.submit()

    def onAttach(self):
        SimplePanel.onAttach(self)
        self.hookEvents(self.iframe, self.getElement(), self)

    def onDetach(self):
        SimplePanel.onDetach(self)
        self.unhookEvents(self.iframe, self.getElement())

    def setTarget(self, target):
        DOM.setAttribute(self.getElement(), "target", target)

    # FormPanelImpl.unhookEvents
    def unhookEvents(self, iframe, form):
        # these might be wrong, need testing.
        iframe.removeEventListener("load", self._onload_listener, True)
        form.removeEventListener("onsubmit", self._onsubmit_listener, True)

Factory.registerClass('pyjamas.ui.FormPanel', FormPanel)

