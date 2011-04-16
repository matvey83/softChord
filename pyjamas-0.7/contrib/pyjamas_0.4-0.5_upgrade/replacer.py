#!/usr/bin/env python

""" This is a Pre-0.5 to Post-0.5 Application Upgrade Script.

    This program REWRITES your application - everything in the
    entire current working directory - modifying the import statements.
    The task of adapting applications is boring and laborious, so
    why waste time when you can run this script, and it'll be done
    in seconds.

    Please ensure that you do not have any import statements in the following
    syntax (do NOT use backslashes):
                                            v
    from pyjamas.ui import HorizontalPanel, \ <--
                           HTML             ^

    Older style statements such as 'from ui import HTML' are NOT covered but
    if you wish to adapt this code to do so, make a second 'searchfor'
    using 'from ui import ' instead of 'from pyjamas.ui import ' below.


    *****************
    **** WARNING ****

    You are expected to take your own precautions to mitigate the destruction
    of your source code, by utilising suitable protection measures such as
    source revision control.

    Absolutely no responsibility WHATSOEVER is, will or can be accepted for
    your failure to take basic precautions, whether you have or have not
    read, or have or have not accepted this warning.

    *****************
    *****************
"""

import sys
import os

def is_in_top_level_ui(modname):
    """ these can be imported 'from pyjamas.ui import modname'
        everything else must be imported
        'from pyjamas.ui.modname import classname', where modname happens
        to be the same as classname
    """
    if modname == 'Focus':
        return True
    if modname == 'Event':
        return True
    if modname == 'MouseListener':
        return True
    if modname == 'KeboardListener':
        return True
    if modname == 'FocusListener':
        return True
    if modname.startswith("Has") and modname.endswith("Alignment"):
        return True
    return False

def rewritefile(p):
    f = open(p)
    res = ''
    searchfor = "from pyjamas.ui import "
    sl = len(searchfor)
    for l in f.readlines():
        if l.startswith(searchfor):
            mods = l[sl:-1]
            l = ''
            for modname in mods.split(","):
                modname = modname.strip()
                if is_in_top_level_ui(modname):
                    l += "from pyjamas.ui import %s\n" % (modname)
                else:
                    l += "from pyjamas.ui.%s import %s\n" % (modname, modname)
        res += l
    f = open(p, "w")
    f.write(res)
    f.close()

for p in os.listdir("."):
    if p.endswith(".py"):
        rewritefile(p)


