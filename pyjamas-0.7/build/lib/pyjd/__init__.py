
pyjdversion = r'0.7~+pre2'
pyjdinitpth = r'/Users/adzhigir/src/softchord/pyjamas-0.7'

import os
import sys
import ConfigParser

if "--version" in sys.argv:
    print "Version:", pyjdversion
    sys.exit(0)


sys.path += [os.path.join(pyjdinitpth, 'library')]

cp = os.environ.get('HOME', '.')
cp = os.path.join(cp, ".pyjd")
cp = os.path.join(cp, "pyjdrc")
cfg = ConfigParser.ConfigParser()
try:
    cfg.read(cp)
    try:
        engine = cfg.get('gui', 'engine')
    except ConfigParser.NoOptionError:
        engine = None
except:
    engine = None
if engine is None:
    if sys.platform == 'win32':
        engine = 'mshtml'
    else:
        engine = 'hulahop'
if engine == 'pywebkitgtk':
    from pywebkitgtk import *
elif engine == 'hulahop':
    from hula import *
elif engine == 'mshtml':
    from mshtml import *

sys.path = [os.path.join(pyjdinitpth, 'pygtkweb', 'library')] + sys.path

import importers
importers._test_revamp()

