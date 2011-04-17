import gtk
import random

class Test:
    def hello(self, widget, data=None):
        self.l.set_text( random.randint(10,20) )

    def run(self):
        self.b = gtk.Button('Click me !')
        self.b.connect("clicked", self.hello, None)
        self.l = gtk.Label('null')
        self.h = gtk.VBox()
        self.h.add(self.b)
        self.h.add(self.l)
        self.w = gtk.Window()
        self.w.add(self.h)
        self.w.show_all()
        gtk.main()

if __name__=='__main__':
    t = Test()
    t.run()
