class TextBoxBase(FocusWidget):
    def getCursorPos(self):
        try :
            elem = self.getElement()
            tr = elem.document.selection.createRange()
            if tr.parentElement().uniqueID != elem.uniqueID:
                return -1
            return -tr.move("character", -65535)
        except:
            return 0

    def getSelectionLength(self):
        try :
            elem = self.getElement()
            tr = elem.document.selection.createRange()
            if tr.parentElement().uniqueID != elem.uniqueID:
                return 0
            return tr.text and len(tr.text) or 0
        except:
            return 0

    def setSelectionRange(self, pos, length):
        try :
            elem = self.getElement()
            tr = elem.createTextRange()
            tr.collapse(True)
            tr.moveStart('character', pos)
            tr.moveEnd('character', length)
            tr.select()
        except :
            pass

    def getText(self):
        return DOM.getAttribute(self.getElement(), "value") or ""

