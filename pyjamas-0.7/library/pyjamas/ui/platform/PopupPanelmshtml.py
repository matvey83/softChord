#class PopupPanel:
#    
#    # PopupImpl.onShow
#    def onShowImpl(self, popup):
#        frame = doc().createElement('iframe')
#        frame.scrolling = 'no'
#        frame.frameBorder = 0
#        frame.style.position = 'absolute'
#        
#        popup.__frame = frame
#        frame.__popup = popup
#        frame.style.setExpression('left', 'this.__popup.offsetLeft')
#        frame.style.setExpression('top', 'this.__popup.offsetTop')
#        frame.style.setExpression('width', 'this.__popup.offsetWidth')
#        frame.style.setExpression('height', 'this.__popup.offsetHeight')
#        popup.parentElement.insertBefore(frame, popup)
#
#    # PopupImpl.onHide
#    def onHideImpl(self, popup):
#        var frame = popup.__frame
#        frame.parentElement.removeChild(frame)
#        popup.__frame = None
#        frame.__popup = None


