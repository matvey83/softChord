# emulate behaviour of other browsers
def focus(elem):
    # i know this looks weird, but it's to catch the exceptions
    # that might happen on focus and ignore them (the names of which
    # we don't know) but otherwise to create standard errors.
    if elem and hasattr(elem, 'focus'):
        try:
            elem.focus()
        except:
            pass
    else:
        elem.focus()
