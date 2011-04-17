class TextArea(TextBoxBase):
    def getCursorPos(self):
        try :
            elem = self.getElement()
            tr = elem.document.selection.createRange()
            tr2 = tr.duplicate()
            tr2.moveToElementText(elem)
            tr.setEndPoint('EndToStart', tr2)
            return tr.text.length
        except:
            return 0


