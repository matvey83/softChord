#!/usr/bin/python

""" simple creation of three commands, customised for your specific system.
    windows users get a corresponding batch file.  yippeeyaiyay.
"""
version = '0.7~+pre2'

import os
import sys

pyjsbuild = """#!%(exec)s

pyjsversion = r'%(ver)s'
pyjspth = r'%(pyjspth)s'

import os
import sys
sys.path[0:0] = [r'%(pth)s']
sys.path.append(os.path.join(pyjspth, 'pgen'))
import pyjs
pyjs.pyjspth = pyjspth
pyjs.path += [os.path.join(pyjspth, 'library'),
os.path.join(pyjspth, 'addons'),
]

import pyjs.browser
if __name__ == '__main__':
    if "--version" in sys.argv:
        print "Version:", pyjsversion
        sys.exit(0)
    pyjs.browser.build_script()
"""

pyjscompile = """#!%(exec)s

pyjsversion = r'%(ver)s'
pyjspth = r'%(pyjspth)s'

import os
import sys
sys.path[0:0] = [r'%(pth)s']
sys.path.append(os.path.join(pyjspth, 'pgen'))

import pyjs.translator
pyjs.pyjspth = pyjspth
pyjs.path += [os.path.join(pyjspth, 'library')]

if __name__ == '__main__':
    if "--version" in sys.argv:
        print "Version:", pyjsversion
        sys.exit(0)
    pyjs.translator.main()
"""

pyjampiler= """#!%(exec)s

pyjsversion = r'%(ver)s'
pyjspth = r'%(pyjspth)s'

import os
import sys
sys.path[0:0] = [r'%(pth)s']
sys.path.append(os.path.join(pyjspth, 'pgen'))

import pyjs.pyjampiler
pyjs.pyjspth = pyjspth
pyjs.path += [os.path.join(pyjspth, 'library')]

if __name__ == '__main__':
    if "--version" in sys.argv:
        print "Version:", pyjsversion
        sys.exit(0)
    pyjs.pyjampiler.Builder()
"""

pyjdinitpth = os.path.join("pyjd", "__init__.py.in")
pyjdinit = open(pyjdinitpth, "r").read()

batcmdtxt = '''@echo off
set CMD_LINE_ARGS=
:setArgs
if ""%%1""=="""" goto doneSetArgs
set CMD_LINE_ARGS=%%CMD_LINE_ARGS%% %%1
shift
goto setArgs
:doneSetArgs

python "%s.py" %%CMD_LINE_ARGS%%
'''

def make_cmd(prefix, pth, pyjsversion, pyjspth, cmdname, txt):

    if sys.platform == 'win32':
        cmd_name = cmdname + ".py"
    else:
        cmd_name = cmdname

    p = os.path.join(prefix, "bin")
    if not os.path.exists(p):
        os.makedirs(p)

    cmd = os.path.join("bin", cmd_name)
    cmd = os.path.join(prefix, cmd)

    if os.path.exists(cmd):
        if     sys.platform == 'win32' \
           and hasattr(os, "chmod"):
            os.chmod(cmd, 0755)
        os.unlink(cmd)
    f = open(cmd, "w")
    f.write(txt % {'exec': sys.executable, 
                   'ver': pyjsversion,
                   'pyjspth': pyjspth, 
                   'pth': pth})
    f.close()

    if hasattr(os, "chmod"):
        os.chmod(cmd, 0555)

    if sys.platform == 'win32':
        cmd = os.path.join("bin", cmdname)
        cmd = os.path.join(prefix, cmd)
        cmd = os.path.abspath(cmd)
        batcmd = "%s.bat" % cmd
        f = open(batcmd, "w")
        f.write(batcmdtxt % cmd)
        f.close()

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        pth = sys.argv[1]
        pyjspth = pth
    else:
        pth = os.path.abspath(os.getcwd())
        pyjspth = pth
        pth = os.path.join(pth, 'pyjs', 'src')

    if len(sys.argv) == 3:
        prefix = sys.argv[2]
    elif len(sys.argv) == 4:
        prefix = sys.argv[3]
        pyjspth = sys.argv[2]
    else:
        prefix = "."

    make_cmd(prefix, pth, version, pyjspth, "pyjsbuild", pyjsbuild)
    make_cmd(prefix, pth, version, pyjspth, "pyjscompile", pyjscompile)
    make_cmd(prefix, pth, version, pyjspth, "pyjampiler", pyjampiler)

    # create pyjd/__init__.py
    pyjdinitpth = os.path.join("pyjd", "__init__.py")
    f = open(pyjdinitpth, "w")
    f.write(pyjdinit % (version, pyjspth))
    f.close()

