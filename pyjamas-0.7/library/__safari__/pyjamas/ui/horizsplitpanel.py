"""
    Horizontal Split Panel: Left and Right layouts with a movable splitter.

/*
 * Copyright 2008 Google Inc.
 * Copyright 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
 * 
 * Licensed under the Apache License, Version 2.0 (the "License") you may not
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
 */
"""

class ImplHorizontalSplitPanel:
    """ 
        The Safari implementation which owes its existence entirely to a single
        WebKit bug: http:#bugs.webkit.org/show_bug.cgi?id=9137.
    """
    def __init__(self, panel):
        
      fullSize = "100%"
      ImplHorizontalSplitPanel.__init__(self, panel)
      self.panel.setElemHeight(self.panel.container, fullSize)
      self.panel.setElemHeight(self.panel.getWidgetElement(0), fullSize)
      self.panel.setElemHeight(self.panel.getWidgetElement(1), fullSize)
      self.panel.setElemHeight(self.panel.getSplitElement(), fullSize)

