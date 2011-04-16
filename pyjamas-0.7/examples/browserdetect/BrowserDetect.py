import pyjd

from pyjamas.ui.Label import Label
from pyjamas.ui.RootPanel import RootPanel

class BrowserDetect:
    def onModuleLoad(self):
        self.l = Label()
        RootPanel().add(self.l)
        self.display()

    def display(self):
        self.l.setText("Browser not detected/supported")



if __name__ == '__main__':
    pyjd.setup("./BrowserDetect.html")
    app = BrowserDetect()
    app.onModuleLoad()
    pyjd.run()
