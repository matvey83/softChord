from ui import Button, RootPanel, Label
import Window

def greet(sender):
    Window.alert("Hello, AJAX!")

class Hello:
  def onModuleLoad(self):
    b = Button("Click me", greet)
    RootPanel().add(b)
    if (1 or 0) and 0:
        RootPanel().add(Label("or FAILED"))
    else:
        RootPanel().add(Label("or OK"))
    if 0 & 1 == 0:
        RootPanel().add(Label("& OK"))
    else:
        RootPanel().add(Label("& FAILED"))
    if 1 | 1 != 1:
        RootPanel().add(Label("| FAILED"))
    else:
        RootPanel().add(Label("| OK"))
