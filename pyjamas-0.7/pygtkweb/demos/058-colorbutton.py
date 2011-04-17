#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk

class ColorButtonExample:
    def __init__(self):
        window = gtk.Window()
        window.connect('destroy', lambda w: gtk.main_quit())
        hbox = gtk.HBox()
        window.add(hbox)
        label = gtk.Label('Foreground Color:')
        hbox.pack_start(label, False)
        colorbutton = gtk.ColorButton(gtk.gdk.color_parse('red'))
        colorbutton.set_use_alpha(True)
        colorbutton.set_title('Select a Color')
        colorbutton.set_alpha(32767)
        colorbutton.connect('color-set', self.color_set_cb)
        hbox.pack_start(colorbutton)
        window.show_all()
        return

    def color_set_cb(self, colorbutton):
        color = colorbutton.get_color()
        alpha = colorbutton.get_alpha()
        print 'You have selected the color:', \
              color.red, color.green, color.blue, 'with alpha:', alpha
        return

def main():
    gtk.main()


if __name__ == '__main__':
    cbe = ColorButtonExample()
    main()
