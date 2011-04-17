"""
* Copyright 2008 Fred Sauer
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



from pyjamas.ui.Widget import Widget

"""*
* {@link com.allen_sauer.gwt.dnd.client.util.DOMUtil} default
* cross-browser implementation.
"""
class DOMUtilImpl:
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#cancelAllDocumentSelections()
    """
    def cancelAllDocumentSelections():
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getBorderLeft(Element)
    """
    def getBorderLeft(elem):
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getBorderTop(Element)
    """
    def getBorderTop(elem):
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getClientHeight(Element)
    """
    def getClientHeight(Element elem):
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getClientWidth(Element)
    """
    def getClientWidth(elem):
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getHorizontalBorders(Widget)
    """
    def getHorizontalBorders(self, widget):
        return widget.getOffsetWidth() - getClientWidth(widget.getElement())
    
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getNodeName(Element)
    """
    def getNodeName(self, elem):
        JS("""
        return elem.nodeName;
        """)
    
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#getVerticalBorders(Widget)
    """
    def getVerticalBorders(self, widget):
        return widget.getOffsetHeight() - getClientHeight(widget.getElement())
    
    
    def isOrContains(parent, child):
    
    """*
    * @see com.allen_sauer.gwt.dnd.client.util.DOMUtil#setStatus(String)
    """
    def setStatus(self, text):
        JS("""
        $wnd.status = text;
        """)
    


