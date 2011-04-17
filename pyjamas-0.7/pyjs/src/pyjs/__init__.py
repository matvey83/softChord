import os

# default to None indicates 'relative paths' so that as a self-contained
# archive, pyjs can run its tests.
pyjspth = None

path = [os.path.abspath('')]

if os.environ.has_key('PYJSPATH'):
    for p in os.environ['PYJSPATH'].split(os.pathsep):
        p = os.path.abspath(p)
        if os.path.isdir(p):
            path.append(p)

