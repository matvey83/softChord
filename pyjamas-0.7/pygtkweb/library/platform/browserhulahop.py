def mash_attrib(name, joiner='-'):
    res = ''
    for c in name:
        if c.isupper():
            res += joiner + c.lower()
        else:
            res += c
    return res

def round_val(val, digits):
    return round(val, digits)

def get_listener(eventtype, item):
    #print "get_listener", eventtype, item
    #print "listeners", listeners
    if item is None:
        return None
    if hasattr(item, "__instance__"):
        ret = listeners.get(eventtype, {}).get(item.__instance__)
    else:
        ret = listeners.get(eventtype, {}).get(hash(item))
    return ret

def set_listener(eventtype, item, listener):
    #print "set_listener", eventtype, item, listener
    if not listeners.has_key(eventtype):
        listeners[eventtype] = {}
    if hasattr(item, "__instance__"):
        listeners[eventtype][item.__instance__] = listener
    else:
        listeners[eventtype][hash(item)] = listener

class Element:
    def __init__(self, tag=None, element=None):
        if tag is not None:
            self.element = doc().createElement(tag)
        elif element is not None:
            self.element = element
        else:
            raise Exception("Cannot create Element without tag or element")
        
        self.activeEvents = []

    def append(self, element):
        self.element.appendChild(element.element)

    def prepend(self, element):
        self.element.insertBefore(element.element, self.element.firstChild)

    def getX(self):
        obj = self.element
        curleft = 0
        if (obj.offsetParent):
            curleft = obj.offsetLeft
            while obj.offsetParent:
                curleft += obj.offsetParent.offsetLeft
                obj = obj.offsetParent
        return curleft

    def getY(self):
        obj = self.element
        curtop = 0
        if (obj.offsetParent):
            curtop = obj.offsetTop
            while obj.offsetParent:
                curtop += obj.offsetParent.offsetTop
                obj = obj.offsetParent
        return curtop

    def getWidth(self):
        return self.element.offsetWidth

    def getHeight(self):
        return self.element.offsetHeight

    def setWidth(self, width):
        self.setStyle('width',width)

    def setHeight(self, height):
        self.setStyle('height',height)

    def setStyle(self, property, value):
        self.element.style.setProperty(mash_attrib(property), value, "")

    def setPxStyle(self, property, value):
        self.setStyle(property, "%dpx" % value)

    def setPercentStyle(self, property, value):
        self.setStyle(property, "%d%%" % value)

    def getStyle(self, property):
        return this.element.style.getProperty(mash_attrib(property))

    def setProperty(self, property, value):
        self.element.setAttribute(mash_attrib(property), value)

    def getProperty(self, property):
        return this.element.getAttribute(mash_attrib(property))

    def setHTML(self, content):
        self.element.innerHTML = content

    def getHTML(self):
        return self.element.innerHTML

    def on_browser_event(self, view, e, ignore):
        #print "on_browser_event", view, e, ignore
        if not e:
            e = wnd().event
        if e.target:
            targ = e.target
        elif e.srcElement:
            targ = e.srcElement
        while targ and not get_listener(e.type, targ):
            #print "no parent listener", curElem, getParent(curElem)
            targ = targ.parentNode
        if targ and targ.nodeType != 1:
            targ = targ.parentNode

        listener = get_listener(e.type, targ)
        if listener:
            listener.dom_event(e, self)

    def catchEvents(self, name, object):
        name = name[0]
        self.activeEvents.append((name, object))
        if not get_listener(name, self.element):
            set_listener(name, self.element, object)
            mf = get_main_frame()
            mf.addEventListener(self.element, name, self.on_browser_event)

class Document:
    window = Element(element= wnd())
    document = Element(element= doc())
    body = Element(element= doc().body)

    @staticmethod
    def createElement(tag):
        return Element(tag)
    
    @staticmethod
    def append(element):
        doc().body.appendChild(element.element)

    @staticmethod
    def setContent(message):
        doc().body.innerHTML = message

    @staticmethod
    def setTitle(title):
        doc().title = title

