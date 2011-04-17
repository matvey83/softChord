"""
* Copyright 2007 Google Inc.
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




from FocusWidget import FocusWidget
from RichTextAreaImplStandard import RichTextAreaImplStandard


"""*
* Font size enumeration. Represents the seven basic HTML font sizes, as
* defined in CSS.
"""
class FontSize:


    def __init__(self, number):
        self.number = number


    """*
    * Gets the HTML font number associated with this font size.
    *
    * @return an integer from 1 to 7 inclusive
    """
    def getNumber(self):
        return self.number

    def __str__(self):
        return str(self.number)


"""*
* Represents an XX-Small font.
"""
XX_SMALL = FontSize(1)

"""*
* Represents an X-Small font.
"""
X_SMALL = FontSize(2)

"""*
* Represents a Small font.
"""
SMALL = FontSize(3)

"""*
* Represents a Medium font.
"""
MEDIUM = FontSize(4)

"""*
* Represents a Large font.
"""
LARGE = FontSize(5)

"""*
* Represents an X-Large font.
"""
X_LARGE = FontSize(6)

"""*
* Represents an XX-Large font.
"""
XX_LARGE = FontSize(7)

"""*
* Justification enumeration. The three values are <code>left</code>,
* <code>right</code>, <code>center</code>.
"""
class Justification:

    def __init__(self, tag):
        self.tag = tag
  
    def __str__(self):
        return "Justify " + self.tag

"""*
* Center justification.
"""
CENTER = Justification("Center")

"""*
* Left justification.
"""
LEFT = Justification("Left")

"""*
* Right justification.
"""
RIGHT = Justification("Right")



"""*
* A rich text editor that allows complex styling and formatting.
*
* Because some browsers do not support rich text editing, and others support
* only a limited subset of functionality, there are two formatter interfaces,
* accessed via {@link #getBasicFormatter()} and {@link #getExtendedFormatter()}.
* A browser that does not support rich text editing at all will return
* <code>None</code> for both of these, while one that supports only the basic
* functionality will return <code>None</code> for the latter.
*
* <p>
* <img class='gallery' src='RichTextArea.png'/>
* </p>
*
* <h3>CSS Style Rules</h3>
* <ul class="css">
* <li>.gwt-RichTextArea { }</li>
* </ul>
"""
class RichTextArea (FocusWidget) :


    """*
    * Creates a new, blank {@link RichTextArea} object with no stylesheet.
    """
    def __init__(self, **kwargs):
        if not kwargs.has_key('StyleName'): kwargs['StyleName']="gwt-RichTextArea"
        self.impl = RichTextAreaImplStandard()
        FocusWidget.__init__(self, self.impl.getElement(), **kwargs)



    """*
    * Gets the basic rich text formatting interface.
    *
    * @return <code>None</code> if basic formatting is not supported
    """
    def getBasicFormatter(self):
        if self.impl.isBasicEditingSupported():
            return self.impl

        return None


    """*
    * Gets the full rich text formatting interface.
    *
    * @return <code>None</code> if full formatting is not supported
    """
    def getExtendedFormatter(self):
        if self.impl.isExtendedEditingSupported():
            return self.impl

        return None


    def getHTML(self):
        return self.impl.getHTML()


    def getText(self):
        return self.impl.getText()


    def setFocus(self, focused):
        # There are different problems on each browser when you try to focus an
        # unattached rich text iframe, so just cut it off early.
        if self.isAttached():
            self.impl.setFocus(focused)



    def setHTML(self, html):
        self.impl.setHTML(html)


    def setText(self, text):
        self.impl.setText(text)


    def onAttach(self):
        FocusWidget.onAttach(self)
        self.impl.initElement()


    def onDetach(self):
        FocusWidget.onDetach(self)
        self.impl.uninitElement()


# TODO: sort out Element **kwargs for Factory.createWidgetOnElement
#Factory.registerClass('pyjamas.ui.RichTextArea', RichTextArea)

