"""
* Copyright 2008 Google Inc.
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
*
* Licensed under the Apache License, Version 2.0 (the "License"); you may not
* use this file except in compliance with the License. You may obtain a copy of
* the License at
*
* http:#www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
* License for the specific language governing permissions and limitations under
* the License.
"""

from __pyjamas__ import doc, wnd, get_main_frame, JS

from pyjamas import DOM
from pyjamas.Timer import Timer

from RichTextAreaImpl import RichTextAreaImpl
from pyjamas.ui import FontSize
from pyjamas.ui import Justification

elem_focussers = {}

"""*
* Basic rich text platform implementation.
"""
class RichTextAreaImplStandard (RichTextAreaImpl):

    def __init__(self):
        RichTextAreaImpl.__init__(self)
        """*
        * Holds a cached copy of any user setHTML/setText actions until the real
        * text area is fully initialized.  Becomes <code>None</code> after init.
        """
        self.beforeInitPlaceholder = DOM.createDiv()

        """*
        * Set to True when the {@link RichTextArea} is attached to the page and
        * {@link #initElement()} is called.  If the {@link RichTextArea} is detached
        * before {@link #onElementInitialized()} is called, this will be set to
        * False.  See issue 1897 for details.
        """
        self.initializing = False

    def createElement(self):
        return DOM.createElement('iframe')

    def createLink(self, url):
        self.execCommand("CreateLink", url)


    def getBackColor(self):
        return self.queryCommandValue("BackColor")


    def getForeColor(self):
        return self.queryCommandValue("ForeColor")


    def getHTML(self):
        if self.beforeInitPlaceholder is None:
            return self.getHTMLImpl()
        return DOM.getInnerHTML(self.beforeInitPlaceholder)


    def getText(self):
        if self.beforeInitPlaceholder is None:
            return self.getTextImpl()
        return DOM.getInnerText(self.beforeInitPlaceholder)

    def onTimer(self, tid):
        self.elem.contentWindow.document.designMode = 'On'

        # Send notification that the iframe has reached design mode.
        self.onElementInitialized()
        
    def initElement(self):
        # Most browsers don't like setting designMode until slightly _after_
        # the iframe becomes attached to the DOM. Any non-zero timeout will do
        # just fine.
        print "initElement"
        self.initializing = True
        Timer(50, self)

    def insertHorizontalRule(self):
        self.execCommand("InsertHorizontalRule", None)


    def insertImage(self, url):
        self.execCommand("InsertImage", url)


    def insertOrderedList(self):
        self.execCommand("InsertOrderedList", None)


    def insertUnorderedList(self):
        self.execCommand("InsertUnorderedList", None)


    def isBasicEditingSupported(self):
        return True


    def isBold(self):
        return self.queryCommandState("Bold")


    def isExtendedEditingSupported(self):
        return True


    def isItalic(self):
        return self.queryCommandState("Italic")


    def isStrikethrough(self):
        return self.queryCommandState("Strikethrough")


    def isSubscript(self):
        return self.queryCommandState("Subscript")


    def isSuperscript(self):
        return self.queryCommandState("Superscript")


    def isUnderlined(self):
        return self.queryCommandState("Underline")


    def leftIndent(self):
        self.execCommand("Outdent", None)


    def removeFormat(self):
        self.execCommand("RemoveFormat", None)


    def removeLink(self):
        self.execCommand("Unlink", "False")


    def rightIndent(self):
        self.execCommand("Indent", None)


    def selectAll(self):
        self.execCommand("SelectAll", None)


    def setBackColor(self, color):
        self.execCommand("BackColor", color)


    def setFocus(self, focused):
        if focused:
            self.elem.contentWindow.focus()
        else:
            self.elem.contentWindow.blur()


    def setFontName(self, name):
        self.execCommand("FontName", name)


    def setFontSize(self, fontSize):
        self.execCommand("FontSize", str(fontSize))


    def setForeColor(self, color):
        self.execCommand("ForeColor", color)


    def setHTML(self, html):
        if self.beforeInitPlaceholder is None:
            self.setHTMLImpl(html)
        else:
            DOM.setInnerHTML(self.beforeInitPlaceholder, html)



    def setJustification(self, justification):
        if justification == Justification.CENTER:
            self.execCommand("JustifyCenter", None)
        elif justification == Justification.LEFT:
            self.execCommand("JustifyLeft", None)
        elif justification == Justification.RIGHT:
            self.execCommand("JustifyRight", None)



    def setText(self, text):
        if self.beforeInitPlaceholder is None:
            self.setTextImpl(text)
        else:
            DOM.setInnerText(self.beforeInitPlaceholder, text)



    def toggleBold(self):
        self.execCommand("Bold", "False")


    def toggleItalic(self):
        self.execCommand("Italic", "False")


    def toggleStrikethrough(self):
        self.execCommand("Strikethrough", "False")


    def toggleSubscript(self):
        self.execCommand("Subscript", "False")


    def toggleSuperscript(self):
        self.execCommand("Superscript", "False")


    def toggleUnderline(self):
        self.execCommand("Underline", "False")


    def uninitElement(self):
        # Issue 1897: initElement uses a timeout, so its possible to call this
        # method after calling initElement, but before the event system is in
        # place.
        if self.initializing:
            self.initializing = False
            return


        # Unhook all custom event handlers when the element is detached.
        self.unhookEvents()

        # Recreate the placeholder element and store the iframe's contents in it.
        # This is necessary because some browsers will wipe the iframe's contents
        # when it is removed from the DOM.
        html = self.getHTML()
        self.beforeInitPlaceholder = DOM.createDiv()
        DOM.setInnerHTML(self.beforeInitPlaceholder, html)


    def getHTMLImpl(self):
        return self.elem.contentWindow.document.body.innerHTML


    def getTextImpl(self):
        return self.elem.contentWindow.document.body.textContent

    def __gwt_handler(self, view, evt, from_window):
        try:
            evt = get_main_frame().gobject_wrap(evt) # webkit HACK!
        except:
            pass

        listener = DOM.get_listener(self.elem)
        if listener:
            listener.onBrowserEvent(evt);

    def __gwt_focus_handler(self, view, evt, from_window):

        if elem_focussers.get(self.elem, False):
            return

        elem_focussers[self.elem] = True
        self.__gwt_handler(view, evt, from_window)

    def __gwt_blur_handler(self, view, evt, from_window):

        if not elem_focussers.get(self.elem, False):
            return

        elem_focussers[self.elem] = False
        self.__gwt_handler(view, evt, from_window)

    def hookEvents(self):
        elem = self.elem;
        win = elem.contentWindow;

        mf = get_main_frame()
        mf._addWindowEventListener('keydown', self.__gwt_handler, win)
        mf._addWindowEventListener('keyup', self.__gwt_handler, win)
        mf._addWindowEventListener('keypress', self.__gwt_handler, win)
        mf._addWindowEventListener('mousedown', self.__gwt_handler, win)
        mf._addWindowEventListener('mouseup', self.__gwt_handler, win)
        mf._addWindowEventListener('mousemove', self.__gwt_handler, win)
        mf._addWindowEventListener('mouseover', self.__gwt_handler, win)
        mf._addWindowEventListener('mouseout', self.__gwt_handler, win)
        mf._addWindowEventListener('click', self.__gwt_handler, win)

        mf._addWindowEventListener('focus', self.__gwt_focus_handler, win)
        mf._addWindowEventListener('blur', self.__gwt_blur_handler, win)


    def onElementInitialized(self):
        # Issue 1897: This method is called after a timeout, during which time the
        # element might by detached.
        if not self.initializing:
            return

        print "onElementInit", DOM.getInnerHTML(self.beforeInitPlaceholder)
        self.initializing = False

        RichTextAreaImpl.onElementInitialized(self)

        # When the iframe is ready, ensure cached content is set.
        if self.beforeInitPlaceholder is not None:
            self.setHTMLImpl(DOM.getInnerHTML(self.beforeInitPlaceholder))
            self.beforeInitPlaceholder = None



    def setHTMLImpl(self, html):
        self.elem.contentWindow.document.body.innerHTML = html;


    def setTextImpl(self, text):
        self.elem.contentWindow.document.body.textContent = text;


    def unhookEvents(self):
        print """ TODO: RichTextEditor.unhookEvents:
        var elem = this.elem;
        var wnd = elem.contentWindow;

        wnd.removeEventListener('keydown', elem.__gwt_handler, true);
        wnd.removeEventListener('keyup', elem.__gwt_handler, true);
        wnd.removeEventListener('keypress', elem.__gwt_handler, true);
        wnd.removeEventListener('mousedown', elem.__gwt_handler, true);
        wnd.removeEventListener('mouseup', elem.__gwt_handler, true);
        wnd.removeEventListener('mousemove', elem.__gwt_handler, true);
        wnd.removeEventListener('mouseover', elem.__gwt_handler, true);
        wnd.removeEventListener('mouseout', elem.__gwt_handler, true);
        wnd.removeEventListener('click', elem.__gwt_handler, true);

        wnd.removeEventListener('focus', elem.__gwt_focusHandler, true);
        wnd.removeEventListener('blur', elem.__gwt_blurHandler, true);

        elem.__gwt_handler = null;
        elem.__gwt_focusHandler = null;
        elem.__gwt_blurHandler = null;
        """


    def execCommand(self, cmd, param):
        if self.isRichEditingActive(elem):
            # When executing a command, focus the iframe first, since some commands
            # don't take properly when it's not focused.
            setFocus(True)
            self.execCommandAssumingFocus(cmd, param)



    def execCommandAssumingFocus(self, cmd, param):
        self.elem.contentWindow.document.execCommand(cmd, False, param)


    def isRichEditingActive(self, e):
        return str(e.contentWindow.document.designMode).upper() == 'ON'


    def queryCommandState(self, cmd):
        if isRichEditingActive(elem):
            # When executing a command, focus the iframe first, since some commands
            # don't take properly when it's not focused.
            setFocus(True)
            return self.queryCommandStateAssumingFocus(cmd)
        else:
            return False



    def queryCommandStateAssumingFocus(self, cmd):
        return self.elem.contentWindow.document.queryCommandState(cmd)


    def queryCommandValue(self, cmd):
        # When executing a command, focus the iframe first, since some commands
        # don't take properly when it's not focused.
        self.setFocus(True)
        return self.queryCommandValueAssumingFocus(cmd)


    def queryCommandValueAssumingFocus(self, cmd):
        return self.elem.contentWindow.document.queryCommandValue(cmd)



