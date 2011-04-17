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




"""*
* {@link com.allen_sauer.gwt.dnd.client.util.DOMUtil} implementation for
* standard browsers.
"""
class DOMUtilImplStandard(DOMUtilImpl):
    def cancelAllDocumentSelections(self):
        JS("""
        try {
            $wnd.getSelection().removeAllRanges();
        } catch(e) { throw new Error("unselect exception:\n" + e); }
        """)
    
    
    def getBorderLeft(self, elem):
        JS("""
        try {
            var computedStyle = $doc.defaultView.getComputedStyle(elem, null);
            var borderLeftWidth = computedStyle.getPropertyValue("border-left-width");
            return borderLeftWidth.indexOf("px") == -1 ? 0 : parseInt(borderLeftWidth.substr(0, borderLeftWidth.length - 2));
        } catch(e) { throw new Error("getBorderLeft exception:\n" + e); }
        """)
    
    
    def getBorderTop(self, elem):
        JS("""
        try {
            var computedStyle = $doc.defaultView.getComputedStyle(elem, null);
            var borderTopWidth = computedStyle.getPropertyValue("border-top-width");
            return borderTopWidth.indexOf("px") == -1 ? 0 : parseInt(borderTopWidth.substr(0, borderTopWidth.length - 2));
        } catch(e) { throw new Error("getBorderTop: " + e); }
        """)
    
    
    def getClientHeight(self, elem):
        JS("""
        try {
            return elem.clientHeight;
        } catch(e) { throw new Error("getClientHeight exception:\n" + e); }
        """)
    
    
    def getClientWidth(self, elem):
        JS("""
        try {
            return elem.clientWidth;
        } catch(e) { throw new Error("getClientWidth exception:\n" + e); }
        """)
    
    
    def isOrContains(self, parent, child):
        JS("""
        return parent.contains(child);
        """)
    


