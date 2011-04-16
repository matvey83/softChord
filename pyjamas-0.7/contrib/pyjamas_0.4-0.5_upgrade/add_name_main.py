#!/usr/bin/env python
#
# appends onModuleLoad thingy onto application
# pyjamas 0.5 no longer automatically calls onModuleLoad
#

import sys

f = open(sys.argv[1] + ".py", "a+")

f.write("""

if __name__ == '__main__':
    app = %s()
    app.onModuleLoad()
""" % sys.argv[1])
f.close()

