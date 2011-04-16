import pyjd # dummy in pyjs

from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.HTML import HTML
#from pyjamas.ui.NamedFrame import NamedFrame
#from pyjamas.ui.Hyperlink import Hyperlink
from pyjamas.ui.DockPanel import DockPanel
from pyjamas.ui import HasAlignment
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.ScrollPanel import ScrollPanel
from pyjamas import Window
from SinkList import SinkList
from pyjamas import History
import Chapter
from pyjamas.HTTPRequest import HTTPRequest
from BookLoader import ChapterListLoader
#from pyjamas.ui.vertsplitpanel import VerticalSplitPanel

def loadSection(section):

    chapter = Chapter.Chapter()
    chapter.setStyleName("ks-Sink")
    chapter.name = section
    RootPanel().add(chapter)
    chapter.onShow()

class Bookreader:

    def onHistoryChanged(self, token):
        info = self.sink_list.find(token)
        if info:
            self.show(info, False)
        else:
            self.showInfo()

    def onModuleLoad(self):
        section = Window.getLocation().getSearchVar("section")
        if not section:
            self.loadChapters()
        else:
            loadSection(section)

    def loadChapters(self):

        self.curInfo = ''
        self.curSink = None
        self.description = HTML()
        self.sink_list = SinkList()
        self.panel = DockPanel()
        
        self.loadSinks()
        self.sinkContainer = DockPanel()
        self.sinkContainer.setStyleName("ks-Sink")

        #self.nf = NamedFrame("section")
        #self.nf.setWidth("100%")
        #self.nf.setHeight("10000")

        height = Window.getClientHeight()

        self.sp = ScrollPanel(self.sinkContainer)
        #self.sp = VerticalSplitPanel()
        self.sp.setWidth("100%")
        self.sp.setHeight("%dpx" % (height-110))

        #self.sp.setTopWidget(self.sinkContainer)
        #self.sp.setBottomWidget(self.nf)
        #self.sp.setSplitPosition(10000) # deliberately high - max out.

        vp = VerticalPanel()
        vp.setWidth("100%")
        vp.setHeight("100%")
        vp.add(self.description)
        vp.add(self.sp)

        self.description.setStyleName("ks-Intro")

        self.panel.add(self.sink_list, DockPanel.WEST)
        self.panel.add(vp, DockPanel.CENTER)

        self.panel.setCellVerticalAlignment(self.sink_list,
                                            HasAlignment.ALIGN_TOP)
        self.panel.setCellWidth(vp, "100%")
        self.panel.setCellHeight(vp, "100%")

        Window.addWindowResizeListener(self)

        History.addHistoryListener(self)
        RootPanel().add(self.panel)


    def onWindowResized(self, width, height):
        self.sink_list.resize(width, height)
        self.sp.setHeight("%dpx" % (height-110))

    def show(self, info, affectHistory):
        if info == self.curInfo:
            return
        self.curInfo = info

        #Logger.write("showing " + info.getName())
        if self.curSink is not None:
            self.curSink.onHide()
            #Logger.write("removing " + self.curSink)
            self.sinkContainer.remove(self.curSink)

        self.curSink = info.getInstance()
        self.sink_list.setSinkSelection(info.getName())
        self.description.setHTML(info.getDescription())

        if (affectHistory):
            History().newItem(info.getName())

        self.sinkContainer.add(self.curSink, DockPanel.CENTER)
        self.sinkContainer.setCellWidth(self.curSink, "100%")
        self.sinkContainer.setCellHeight(self.curSink, "100%")
        self.sinkContainer.setCellVerticalAlignment(self.curSink,
                                                    HasAlignment.ALIGN_TOP)
        self.curSink.onShow()
        
    def loadSinks(self):
        HTTPRequest().asyncGet("contents.txt", ChapterListLoader(self))

    def setChapters(self, chapters):
        for l in chapters:
            name = l[0]
            desc = l[1]
            self.sink_list.addSink(Chapter.init(name, desc))

        #Show the initial screen.
        initToken = History.getToken()
        if len(initToken):
            self.onHistoryChanged(initToken)
        else:
            self.showInfo()


    def showInfo(self):
        self.show(self.sink_list.sinks[0], False)


if __name__ == '__main__':
    pyjd.setup("./public/Bookreader.html")
    app = Bookreader()
    app.onModuleLoad()
    pyjd.run()
