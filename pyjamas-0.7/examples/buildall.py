#!/usr/bin/env python
import os, sys, glob

options = " ".join(sys.argv[1:])
if not options:
    options = "-O"
for pyjsbuild in ('../bin/pyjsbuild.py', '../bin/pyjsbuild', None):
    if os.path.exists(pyjsbuild):
        break
if not pyjsbuild:
    sys.stderr.write("Cannot find pyjsbuild")
    sys.exit(1)

def guessMainScriptName(d):
    if os.path.isfile('build.sh'):
        for line in file('build.sh'):
            line = line.strip()
            if not line or line.startswith('#'): continue
            name = line.split()[-1]
            f = name + '.py'
            if os.path.isfile(f): return name
    for f in glob.glob('*.py'):
        name, ext = os.path.splitext(f)
        if name.lower() in d.lower(): return name
    return ''

for d in os.listdir('.'):
    if os.path.isdir(d):
        os.chdir(d)
        try:
            if os.path.isdir('output'): continue
            name = guessMainScriptName(d)
            if not name: continue
            f = name + '.py'
            print("********** Building %s **********" % name.upper())
            os.system("python ../%s %s %s" % (pyjsbuild, options, f))
        finally:
            #raw_input('Press any key')
            os.chdir("..")
