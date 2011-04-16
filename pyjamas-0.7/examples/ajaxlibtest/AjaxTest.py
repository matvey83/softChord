from pyjamas.ui.Button import Button
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.HTML import HTML
from pyjamas import Window
from pyjamas import DOM
import pyjslib
from __pyjamas__ import JS, doc
import dynamic

def greet(sender):

    JS("""
       test_fn();
    """)

class AjaxTest:

    ClickMe = "Click me"

    def onModuleLoad(self):

        b = Button(self.ClickMe, greet)
        RootPanel().add(b)

        # dynamically loads public/test.cache.js.

        dynamic.ajax_import("test.cache.js", names = ['test_fn'])

if __name__ == '__main__':
    x = AjaxTest()
    x.onModuleLoad()

