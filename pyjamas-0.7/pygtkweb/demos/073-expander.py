#!/usr/bin/env python

import time
import pygtk
pygtk.require('2.0')
import gtk

class ExpanderExample:
    def __init__(self):
        window = gtk.Window()
        window.connect('destroy', lambda w: gtk.main_quit())
        expander = gtk.Expander(None)
        window.add(expander)
        hbox = gtk.HBox()
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
        label = gtk.Label(' Folder Time')
        hbox.pack_start(image)
        hbox.pack_start(label)
        expander.set_label_widget(hbox)
        expander.connect('notify::expanded', self.expanded_cb)
        window.show_all()
        return

    def expanded_cb(self, expander, params):
        if expander.get_expanded():
            label = gtk.Label(time.ctime())
            label.show()
            expander.add(label)
        else:
            expander.remove(expander.child)
        return

def main():
    gtk.main()
    return

if __name__ == "__main__":
    ee = ExpanderExample()
    main()
