replacer.py
-----------

The ui classes have been restructured so that ui.py is not one whopping
great file.  javascript cache output is therefore dramatically reduced.

This tool takes classes, looks for "from pyjamas.ui import X,Y,Z"
and outputs:
from pyjamas.ui.X import X
from pyjamas.ui.Y import X
from pyjamas.ui.Z import Z

*except* for HasAlignment, HasVerticalAlignment and HasHorizontalAlignment



add_name_main.py
----------------

"python add_name_main.py AppName" will add a code fragment to the end
of AppName.py, to create an instance of the AppName() class and call
the onModuleLoad() function in it.

The old method - automatic calling of onModuleLoad() in a class which is
identical to the module name - is no longer supported.

