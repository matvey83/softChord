#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk

class ComboBoxEntryAdvancedExample:
    def __init__(self):
        window = gtk.Window()
        window.connect('destroy', lambda w: gtk.main_quit())
        comboboxentry = gtk.ComboBoxEntry()
        window.add(comboboxentry)
        liststore = gtk.ListStore(str)
        comboboxentry.set_model(liststore)
        liststore.append(['Apple'])
        liststore.append(['Cherry'])
        liststore.append(['Blueberry'])
        liststore.append(['Grape'])
        liststore.append(['Peach'])
        liststore.append(['Raisin'])
        comboboxentry.set_text_column(0)
        comboboxentry.child.connect('changed', self.changed_cb)
        comboboxentry.set_active(0)
        window.show_all()
        return

    def changed_cb(self, entry):
        print 'I like', entry.get_text(), 'pie'
        return

def main():
    gtk.main()
    return

if __name__ == "__main__":
    bcb = ComboBoxEntryAdvancedExample()
    main()
