import pyjd # this is dummy in pyjs.

from pyjamas.ui.RootPanel import RootPanelCls, RootPanel, manageRootPanel
from pyjamas.ui.Button import Button
from pyjamas.ui.FocusPanel import FocusPanel
from pyjamas.ui.KeyboardListener import KeyboardHandler
from pyjamas.ui.ClickListener import ClickHandler
from pyjamas.ui.HTML import HTML
from pyjamas import Window
from pyjamas import DOM
from __pyjamas__ import doc

class RootPanelListener(RootPanelCls, KeyboardHandler, ClickHandler):
    def __init__(self, Parent, *args, **kwargs):
        self.Parent = Parent
        self.focussed = False
        RootPanelCls.__init__(self, *args, **kwargs)
        ClickHandler.__init__(self)
        KeyboardHandler.__init__(self)

        self.addClickListener(self)
        self.addKeyboardListener(self)

    def onClick(self, Sender):
        self.focussed = not self.focussed
        self.Parent.setFocus(self.focussed)

        txt = self.focussed and 'yes. now press keys' or 'no. keys fail now'
        self.add(HTML('focus: %s' % txt))

    def onKeyDown(self, sender, keyCode, modifiers = None):
        self.add(HTML('keyDOWN: %d' % keyCode))

def heightset(fred):
    DOM.setStyleAttribute(doc().body, 'height', '100%')

def marginset(fred):
    DOM.setStyleAttribute(doc().body, 'margin', '0px')

if __name__ == '__main__':

    pyjd.setup("public/ClickableRootPanel.html")

    bh = Button("Click me to set body height to 100%", heightset,
               StyleName='teststyle')
    b = Button("Click me to set body margin to 0", marginset,
               StyleName='teststyle')
    h = HTML("<b>Hello World</b> - watch for focus highlighting after click",
             StyleName='teststyle')

    panel = FocusPanel(Widget=h)
    gp = RootPanelListener(panel, StyleName='rootstyle')

    # as this is replacing the 'normal' usage of RootPanel(),
    # it is necessary to add this in 'by hand' so that the
    # window-close notification is 'hooked into', and so when
    # the browser window is closed, cleanups (onDetach) will
    # be triggered.
    #
    # calling manageRootPanel (with the default arg id=None)
    # also has the advantage that RootPanel(id=None) will
    # 'pick up' the above RootPanelListener instance, meaning
    # that you don't need to have a silly global variable
    # all over the place, you can just use the standard pyjamas
    # API as normal.
    #
    # kinda cute.

    manageRootPanel(gp)

    info = """Click anywhere in the Root (grey) to activate key input;
            click again to disable it.  Note the focus highlighting
            that occurs on the "Hello World" HTML box.
    <br /> <br />
    The CSS style has been set to 100% width
    and the margin to 100px.  Even though it is the "body" - root
    element, clicking outside the margin (indicated by the black border)
    will NOT activate key input.
    <br /><br />
    Note that many browsers screw up the sizes of the window when the
    margin is set as well as width or height to 100%, as evidenced by
    the black border being off the screen.  (Normally, you would add a
    WindowResize Listener which received the window size and then
    directly adjusted the CSS width and height of the body element
    to correct these problems (!) or, much better, add a SimplePanel
    on which the appropriate (100% width+height) CSS styles are set).
    <br /> <br />
    However that's not the issue: the point is that you <b>must</b>
    actually set the body to be 100% of the screen area in order to
    receive click events, and the above highlights why it is important
    to set margin and padding of body to 0 as well, and also to not
    set any borders.
    <br /> <br />
    Click the button to change the margin on the document "body" tag
    to zero, in order to test this out.  Note that the border may still
    be off the screen, even when the margin is zero.
    <br /> <br />
    """

    RootPanel().add(panel)
    RootPanel().add(b)
    RootPanel().add(bh)
    RootPanel().add(HTML(info))

    pyjd.run()
