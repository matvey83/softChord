#!/usr/bin/env python
#
# converts app to pyjd
#

import sys

lines = open(sys.argv[1] + ".py", "r").readlines()

txt = ''
found = 0
txt2 = ''
for l in lines:
    if found:
        txt2 += l
        continue
    if l.startswith("if __name__") and l.index("__main__") > 0:
        found = 1
    txt += l

if not found:
    print "app does not have 'if __name__ == '__main__'' so giving up"
    sys.exit(0)

f = open(sys.argv[1] + ".py", "w")

f.write("""
import pyjd  # this is dummy in pyjs
%s
    # load HTML file (dummy in pyjs)
    pyjd.setup("./public/%s.html")
%s
    pyjd.run() # start pyjd app (dummy in pyjs)
""" % (txt, sys.argv[1], txt2))

f.close()

