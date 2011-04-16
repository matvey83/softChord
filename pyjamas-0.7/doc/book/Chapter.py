from Sink import Sink, SinkInfo
from pyjamas.ui.HTML import HTML
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.HTMLPanel import HTMLPanel
from pyjamas.ui.Hyperlink import Hyperlink
from BookLoader import ChapterLoader
from pyjamas.HTTPRequest import HTTPRequest
from pyjamas import Window
from pyjamas.Timer import Timer

def escape(txt, esc=1):
    if not esc:
        return txt
    txt = txt.replace("&", "&amp;")
    txt = txt.replace("<", "&lt;")
    txt = txt.replace(">", "&gt;")
    txt = txt.replace("%", "&#37;")
    return txt

def sect_markup(txt, name):

    res = ''
    idx = 0
    links = []

    while 1:
        prev_idx = idx
        idx = txt.find("L#{", idx)
        if idx == -1:
            res += txt[prev_idx:]
            break

        beg = txt[prev_idx:idx]
        idx += 3
        i = txt.find("}", idx)
        if i == -1:
            res += txt[prev_idx:]
            break

        if i == len(txt)-1:
            url = txt[idx:]
            end = ''
        else:
            url = txt[idx:i]
            end = txt[i+1:]

        res += beg
        idx = i+1

        page_url = "%s_" % name
        page_url += url.lower()
        i = HTMLPanel.createUniqueId()

        res += "<span id='%s'></span>" % str(i)

        links.append([i, Hyperlink(url, False, page_url)])

    if not links:
        return HTML(res)

    p = HTMLPanel(res)

    for il in links:
        i = il[0]
        l = il[1]
        p.add(l, i)

    return p
 
def urlmap(txt, esc=1):
    idx = txt.find("http://")
    if idx == -1:
        idx = txt.find("https://")
    if idx == -1:
        return escape(txt, esc)
    for i in range(idx+7, len(txt)):
        c = txt[i]
        if c == ' ' or c == '\n' or c == '\t' or c == ',' or c == '<' or c == ')' or c == '(' or c == '>':
            i -= 1
            break
        # full-stop space test
        if i != len(txt)-1:
            c1 = txt[i+1]
            if (c1 == ' ' or c1 == '\n') and (c == '.' or c == ':'):
                i -= 1
                break

    i += 1

    beg = txt[:idx]
    if i == len(txt):
        url = txt[idx:]
        end = ''
    else:
        url = txt[idx:i]
        end = txt[i:]
    txt = escape(beg, esc) + "<a href='%s'>" % url
    txt += "%s</a>" % escape(url) + urlmap(end, esc)
    return txt
 
def ts(txt, esc=1):
    l = txt.split('\n')
    r = []
    for line in l:
        line = line.replace("%", "&#37;")
        r.append(urlmap(line, esc))
    return '<br />'.join(r)

def qr(line):
    return line.replace("'", "&#39;")

class Chapter(Sink):
    def __init__(self):

        Sink.__init__(self)

        self.vp = VerticalPanel()
        self.initWidget(self.vp)
        self.loaded = False

    def onShow(self):

        if self.loaded:
            return 

        self.name = self.name.replace(" ", "_")
        self.name = self.name.lower()
        HTTPRequest().asyncGet("%s.txt" % self.name, ChapterLoader(self))

    def setChapter(self, text):
        self.loaded = True

        self.text = text + '\n'

        self.ul_stack1 = 0
        self.ul_stack2 = 0
        self.doing_code = 0
        self.custom_style = False
        self.txt = ''
        self.para = ''
        self.up_to = 0

        Timer(1, self)

    def onTimer(self, sender):

        count = 0
        while count < 10:
            count += 1
            idx = self.text.find("\n", self.up_to)
            if idx < 0:
                self.text = None
                break
            self.process_line(self.text[self.up_to:idx])
            self.up_to = idx+1

        if self.text:
            Timer(1, self)


    def process_line(self, line):

        if self.doing_code:
            if line == "}}":
                self.doing_code = 0
                self.custom_style = False
                line = "</pre>"
                self.txt += line
                panel = sect_markup(self.txt, self.name)
                self.vp.add(panel)
                self.txt = ''
                return
            if line:
                if not self.custom_style:
                    self.txt += escape(line)
                else:
                    self.txt += line
            self.txt += "\n"
            return
            
        line = line.strip()
        ul_line = False
        ul_line2 = False
        addline = ''
        add = False
        addpara = False
        if not line:
            line = ""
            addpara = True
        elif line[:2] == "{{":
            self.doing_code = 1
            addpara = True
            if len(line) > 4 and line[2] == '-':
                addline = "<pre class='chapter_%s'>" % line[3:]
                self.custom_style = True
            elif len(line) > 2:
                addline = "<pre class='chapter_code'>%s" % line[2:]
            else:
                addline = "<pre class='chapter_code'>"
        elif line[:2] == '= ' and line[-2:] == ' =':
            addline = "<h1 class='chapter_heading1>%s</h1>" % qr(line[2:-2])
            add = True
            addpara = True
        elif line[:3] == '== ' and line[-3:] == ' ==':
            addline = "<h2 class='chapter_heading2>%s</h2>" % qr(line[3:-3])
            add = True
            addpara = True
        elif line[:2] == '* ':
            if not self.ul_stack1:
                self.txt += "<ul class='chapter_list1'>\n"
            addline = "<li class='chapter_listitem1'/>%s\n" % ts(line[2:], 0)
            self.ul_stack1 = True
            ul_line = True
            addpara = True
        elif line[:3] == '** ':
            if not self.ul_stack2:
                self.txt += "<ul class='chapter_list2'>\n"
            addline = "<li class='chapter_listitem2'/>%s\n" % ts(line[2:], 0)
            self.ul_stack2 = True
            ul_line2 = True
            ul_line = True
        if self.ul_stack2 and not ul_line2:
            self.ul_stack2 = False
            self.txt += "</ul>\n"
        if self.ul_stack1 and not ul_line:
            self.ul_stack1 = False
            self.txt += "</ul>\n"
        if addline:
            self.txt += addline + "\n"
        elif line:
            line = line.replace("%", "&#37;")
            self.para += line + "\n"
        if not self.ul_stack2 and not self.ul_stack1 and not self.doing_code :
            add = True
        if self.para and addpara:
            self.para = "<p class='chapter_para'>%s</p>" % urlmap(self.para, 0)
            panel = sect_markup(self.para, self.name)
            self.vp.add(panel)
            self.para = ''
        if add:
            panel = sect_markup(self.txt, self.name)
            self.vp.add(panel)
            self.txt = ''

    def onError(self, text, code):
        self.vp.clear()
        self.vp.add(HTML("TODO: Chapter '%s' not loaded" % self.name))
        self.vp.add(HTML(text))
        self.vp.add(HTML(code))
        
def init(name, desc):
    return SinkInfo(name, desc, Chapter)

