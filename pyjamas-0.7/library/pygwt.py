from __pyjamas__ import get_main_frame, doc, JS

sNextHashId = 0

def getNextHashId():
    global sNextHashId
    sNextHashId += 1
    return sNextHashId

def getHashCode(o):
    JS("""
    return (o == null) ? 0 :
        (o.$H ? o.$H : (o.$H = pygwt_getNextHashId()))
    """)

def getModuleName():
    import os
    import sys
    mod_name = sys.argv[0]
    mod_name = os.path.split(mod_name)[1]
    mod_name = os.path.spliext(mod_name)[0]
    return mod_name

def getModuleBaseURL():
    
    # get original app base
    s = get_main_frame().getUri()
    #s = doc().location.href
    
    # Pull off any hash.
    i = s.find('#')
    if i != -1:
        s = s[:i]
    
    # Pull off any query string.
    i = s.find('?')
    if i != -1:
        s = s[:i]
    
    # Rip off everything after the last slash.
    i = s.rfind('/')
    if i != -1:
        s = s[:i]

    if len(s) > 0:
        return s + "/"
    return ""
