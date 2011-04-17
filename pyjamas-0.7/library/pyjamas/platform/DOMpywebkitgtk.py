def getAbsoluteLeft(elem):
    # Unattached elements and elements (or their ancestors) with style
    # 'display: none' have no offsetLeft.
    if (elem.offsetLeft is None) :
        return 0

    left = 0
    curr = elem.parentNode
    if (curr) :
        # This intentionally excludes body which has a None offsetParent.
        while (curr.offsetParent) :
            left -= curr.scrollLeft
            curr = curr.parentNode
    
    while (elem) :
        left += elem.offsetLeft

        # Safari bug: a top-level absolutely positioned element includes the
        # body's offset position already.
        parent = elem.offsetParent
        if (parent and (parent.tagName == 'BODY') and
                (getStyleAttribute(elem, 'position') == 'absolute')) :
            break

        elem = parent
    
    return left

def getAbsoluteTop(elem):
    # Unattached elements and elements (or their ancestors) with style
    # 'display: none' have no offsetTop.
    if (elem.offsetTop is None) :
        return 0

    top = 0
    curr = elem.parentNode
    if (curr) :
        # This intentionally excludes body which has a None offsetParent.
        while (curr.offsetParent) :
            top -= curr.scrollTop
            curr = curr.parentNode
    
    while (elem) :
        top += elem.offsetTop

        # Safari bug: a top-level absolutely positioned element includes the
        # body's offset position already.
        parent = elem.offsetParent
        if (parent and (parent.tagName == 'BODY') and
                (getStyleAttribute(elem, 'position') == 'absolute')) :
            break
        
        elem = parent
    
    return top

