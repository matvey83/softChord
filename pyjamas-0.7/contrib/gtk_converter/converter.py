import gtk
import gtk.glade

import sys
sys.path.append("../../pyjs/") # lkcl: quick hack

from pyjs import *

def clicked(widget=None):
  code = buf1.get_text(*buf1.get_bounds())
  output = cStringIO.StringIO()
  mod = compiler.parse(code)
  module = name.get_text()
  t = Translator(module,mod,output)
  buf2.set_text(output.getvalue())


xml = gtk.glade.XML('convert.glade')
t1 = xml.get_widget('textview1')
t2 = xml.get_widget('textview2')
btn = xml.get_widget('btnConvert')
buf1 = gtk.TextBuffer()
buf2 = gtk.TextBuffer()
t1.set_buffer(buf1)
t2.set_buffer(buf2)
name = xml.get_widget('entryname')

btn.connect('clicked',clicked)
window = xml.get_widget('window1')
import sys
window.connect('destroy',sys.exit)
window.show()

gtk.main()
