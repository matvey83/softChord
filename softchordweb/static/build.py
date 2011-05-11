#!/bin/python
import os, shutil, subprocess, sys

STATIC_DIR = os.path.abspath(os.path.dirname(__file__))

os.chdir(STATIC_DIR)

# Remove the previous output dir:
out_dir = os.path.join(STATIC_DIR, "output")
if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)


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


# Copy the custom main page file:
shutil.copyfile(os.path.join(STATIC_DIR, "softchordweb-custom.html"), os.path.join(out_dir, "softchordweb-custom.html"))
