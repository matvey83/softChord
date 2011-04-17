# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# Pyjamas Widget Factory.  register widgets with this module,
# for dynamic use in applications.  please observe namespaces.
#
# * pyjamas.ui namespace is used for widgets in library/pyjamas/ui

#from __pyjamas__ import doc
from pyjamas import log
from pyjamas import DOM

factory = {}

def registerClass(name, kls):
    global factory
    factory[name] = kls

def lookupClass(name):
    return factory[name]

def createWidgetOnElement(element):
    fc = DOM.getAttribute(element, 'id')
    lbr = fc.find("(")
    klsname = fc[:lbr]
    txtargs = fc[lbr+1:-1]
    args = []
    kwargs = {}
    for arg in txtargs.split(','):
        findeq = arg.find('=')
        if findeq == -1:
            args.append(arg)
        else:
            k = arg[:findeq]
            v = arg[findeq+1:]
            if ((v[0] == "'" and v[-1] == "'") or
                (v[0] == '"' and v[-1] == '"')):
                # string - strip quotes
                v = v[1:-1]
            else:
                # assume it's an int
                v = int(v)
            kwargs[k] = v

    kwargs['Element'] = element
    return lookupClass(klsname)(*args, **kwargs)
    
def addPyjamasNameSpace():
    doc().createElementNS("urn:schemas-pyjs-org:pyjs")
    #try:
    #    ns = doc().namespaces.item("pyjs")
    #except:
    #    doc().namespaces.add("pyjsinit", "urn:schemas-pyjs-org:pyjs")
        #doc().createStyleSheet().cssText = "v\\:*{behavior:url(#default#VML);}"


