"""
* Copyright 2007 Fred Sauer
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


from pyjamas import DOM


"""*
* {@link com.allen_sauer.gwt.dnd.client.util.DOMUtil} implementation for
* Webkit/Safari.
"""
class DOMUtilImplSafari(DOMUtilImplStandard):
    def cancelAllDocumentSelections(self):
        JS("""
        // While all Safari/Webkit release appear to define the 'collapse' function,
        // this function results in "Error: TYPE_MISMATCH_ERR: DOM Exception 17"
        // on Safari 3.0.4 (5523.10) on Mac OS X Version 10.5 (Leopard)
        // So, newer Safari use 'removeAllRanges', older Safari fall back to 'collapse'
        var s = $wnd.getSelection();
        if (s.removeAllRanges) {
            s.removeAllRanges();
        } else {
            s.collapse();
        }
        """)
    
    
    def getBorderLeft(self, elem):
        JS("""
        var computedStyle = $doc.defaultView.getComputedStyle(elem, null);
        if (computedStyle != null) {
            var borderLeftWidth = computedStyle.getPropertyValue("border-left-width");
            return borderLeftWidth.indexOf("px") == -1 ? 0 : parseInt(borderLeftWidth.substr(0, borderLeftWidth.length - 2));
        } else {
            // When elem is hidden
            return 0;
        }
        """)
    
    
    def getBorderTop(self, elem):
        JS("""
        var computedStyle = $doc.defaultView.getComputedStyle(elem, null);
        if (computedStyle != null) {
            var borderTopWidth = computedStyle.getPropertyValue("border-top-width");
            return borderTopWidth.indexOf("px") == -1 ? 0 : parseInt(borderTopWidth.substr(0, borderTopWidth.length - 2));
        } else {
            // When elem is hidden
            return 0;
        }
        """)
    
    
    def getClientHeight(self, elem):
        JS("""
        return elem.clientHeight || 0;
        """)
    
    
    def getClientWidth(self, elem):
        JS("""
        return elem.clientWidth || 0;
        """)
    
    
    def isOrContains(self, parent, child):
        # While Safari 1.3.2 / Safari 2.0.4 support the 'contains' method on DOM
        # elements, the method does not appear to return valid results in all cases.
        # Revert to a DOM walk from DOM.isOrHasChild instead.
        return DOM.isOrHasChild(parent, child)
    


