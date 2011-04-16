=================
Development setup
=================

To run tests do the following in this directory.

python2.5 bootstrap.py
./bin/buildout
./bin/test

Note that the spidermonkey test requires that the "js" executable is
in the PATH. The LibTests in the example directory are also run and
checked for javascript exceptions that are not catched.

Also a builder script gets created. see:

./bin/build --help

