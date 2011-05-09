#!/bin/python
import os, shutil, subprocess, sys

MEDIA_DIR = os.path.abspath(os.path.dirname(__file__))

os.chdir(MEDIA_DIR)

# Remove the previous output dir:
out_dir = os.path.join(MEDIA_DIR, "output")
if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)

#options="$*"
#if [ -z $options ] ; then options="-O";fi
#../../pyjamas-0.7/bin/pyjsbuild $options softchordweb

# Complie the app:
#pyjsbuild = os.path.join("..", "..", "pyjamas-0.7", "bin", "pyjsbuild")
#err = subprocess.call([ pyjsbuild, "softchordweb" ])
#if err:
#    print "ERROR"
#    sys.exit(1)


sys.argv.append("softchordweb")

pyjspth = os.path.abspath(os.path.join("..", "..", "pyjamas-0.7"))


#sys.path[0:0] = [r'/Users/adzhigir/src/pyjamas-0.7/pyjs/src']
sys.path[0:0] = [r'%s/pyjs/src' % pyjspth]
sys.path.append(os.path.join(pyjspth, 'pgen'))
import pyjs
pyjs.pyjspth = pyjspth
pyjs.path += [os.path.join(pyjspth, 'library'),
os.path.join(pyjspth, 'addons'),
]

import pyjs.browser
pyjs.browser.build_script()

