from __pyjamas__ import JS, doc, wnd, get_main_frame

listeners = {}

def mash_attrib(name, joiner='-'):
    return name

def get_listener(item):
    pass

def set_listener(item, listener):
    pass

def round_val(val, digits):
    return JS('val.toFixed(digits);')

class Element:
    def __init__(self, tag=None, element=None):
        if tag is not None:
            JS('''
            this.element = $doc.createElement(tag);
            ''')
        elif element is not None:
            self.element = element
        else:
            raise Exception("Cannot create Element without tag or element")
        
        self.element.__ref = self;
        self.activeEvents = []

    def append(self, element):
        JS('''
        this.element.appendChild(element.element);
        ''')

    def prepend(self, element):
        JS('''
        this.element.insertBefore(element.element, self.element.firstChild);
        ''')

    def getX(self):
        JS('''
        var obj = this.element;
        var curleft = 0;
        if (obj.offsetParent) {
            curleft = obj.offsetLeft
            while (obj = obj.offsetParent) {
                curleft += obj.offsetLeft
            }
        }
        return curleft;
        ''')

    def getY(self):
        JS('''
        var obj = this.element;
        var curtop = 0;
        if (obj.offsetParent) {
            curtop = obj.offsetTop
            while (obj = obj.offsetParent) {
                curtop += obj.offsetTop
            }
        }
        return curtop;
        ''')

    def getWidth(self):
        JS('''
        return this.element.offsetWidth;
        ''')

    def getHeight(self):
        JS('''
        return this.element.offsetHeight;
        ''')

    def setWidth(self, width):
        self.setStyle('width',width)

    def setHeight(self, height):
        self.setStyle('height',height)

    def setStyle(self, property, value):
        JS('''
        this.element.style[property] = value;
        ''')

    def setPxStyle(self, property, value):
        self.setStyle(property, "%dpx" % value)

    def setPercentStyle(self, property, value):
        self.setStyle(property, "%d%%" % value)

    def getStyle(self, property):
        JS('''
        return this.element.style[property];
        ''')

    def setProperty(self, property, value):
        JS('''
        //this.element.setAttribute(property,value);
        this.element[property] = value;
        ''')

    def getProperty(self, property):
        JS('''
        //return this.element.getAttribute(property);
        return this.element[property];
        ''')

    def setHTML(self, content):
        JS('''
        this.element.innerHTML = content;
        ''')

    def getHTML(self):
        JS('''
        return this.element.innerHTML;
        ''')

    def on_browser_event(self, view, e, ignore):
        pass

    def catchEvents(self, name, object):
        JS('''
        var tmp = function(e) {
            if (!e) var e = $wnd.event;
            if (e.target) targ = e.target;
            else if (e.srcElement) targ = e.srcElement;
            if (targ.nodeType == 3) targ = targ.parentNode;
            if (targ.__ref)
                object.dom_event(e, targ.__ref);
            else
                object.dom_event(e, null);
        };
        ''')
        name = name[0]
        self.activeEvents.append((name, object))
        JS('''
        var old_callback = this.element['on'+name];
        this.element['on'+name] = function(e){if(old_callback){old_callback(e);}tmp(e);};
        ''')

class Document:
    window = Element(element= JS('$wnd'))
    document = Element(element= JS('$doc'))
    body = Element(element= JS('$doc.body'))

    @staticmethod
    def createElement(tag):
        return Element(tag)
    
    @staticmethod
    def append(element):
        JS('''
        $doc.body.appendChild(element.element);
        ''')

    @staticmethod
    def setContent(message):
        JS('''
        $doc.body.innerHTML = message;
        ''')

    @staticmethod
    def setTitle(title):
        JS('''
        $doc.title = title;
        ''')
