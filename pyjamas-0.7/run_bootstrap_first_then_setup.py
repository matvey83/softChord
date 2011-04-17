# Copyright (C) 2007-2008 The PyAMF Project.
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# See LICENSE for details.

import glob
from distutils.core import setup , run_setup

import sys
import os

keyw = """\
Pyjamas, GUI, Compiler, AJAX, Widget Set
"""

datadir = os.path.join("share", "pyjamas")

bp_data_files = glob.glob(os.path.join("builder", "boilerplate", "*"))
test_files = glob.glob(os.path.join("pyjs", "tests", "*"))
stub_files = glob.glob(os.path.join("stubs", "*"))
addons_data_files = glob.glob(os.path.join("addons", "*.py"))
#pygtkweb_data_files = glob.glob(os.path.join("pygtkweb", "*.py"))

data_files = [
    (os.path.join(datadir, "builder", "boilerplate"), bp_data_files),
    (os.path.join(datadir, "pyjs", "tests"), test_files),
    (os.path.join(datadir, "stubs"), stub_files),
    (os.path.join(datadir, "stubs"), stub_files),
    #(os.path.join(datadir, "pygtkweb"), pygtkweb_data_files)
]

# main purpose of this function is to exclude "output" which
# could have been built by a developer.
def get_files(d):
    res = []
    for p in glob.glob(os.path.join(d, "*")):
        if not p:
            continue
        (pth, fname) = os.path.split(p)
        if fname == "output":
            continue
        if fname == "PureMVC_Python_1_0":
            continue
        if fname[-4:] == ".pyc": # ehmm.. no.
            continue 
        if os.path.isdir(p):
            get_dir(p)
        else:
            res.append(p)
    return res

def get_dir(dirname):
    for d in glob.glob("%s/*" % dirname):
        if os.path.isdir(d):
            (pth, fname) = os.path.split(d)
            expath = get_files(d)
            pth = os.path.join(os.path.join(datadir, dirname), fname)
            data_files.append((pth, expath))
        else:
            data_files.append((os.path.join(datadir, dirname), [d]))

# recursively grab the library and the examples subdirectories - all contents
get_dir("library")
get_dir("examples")

# likewise pyjs/src/pyjs
get_dir(os.path.join("pyjs", "src", "pyjs", "builtin"))
get_dir(os.path.join("pyjs", "src", "pyjs", "lib"))
get_dir(os.path.join("pyjs", "src", "pyjs", "boilerplate"))

#from pprint import pprint
#pprint(data_files)

import distutils.core

if __name__ == '__main__':

    print >> sys.stderr, """
    Have you run bootstrap.py to create bin/pyjsbuild
    and bin/pyjscompile?

    e.g. on Unix systems:

        python bootstrap.py /usr/share/pyjamas /usr
    """

    setup(name = "Pyjamas",
        version = "0.7",
        description = "Pyjamas Widget API for Web applications, in Python",
        long_description = open('README', 'rt').read(),
        url = "http://pyjs.org",
        author = "The Pyjamas Project",
        author_email = "lkcl@lkcl.net",
        keywords = keyw,
        packages=["pyjs", "pyjd"],
        package_dir = {'pyjs': os.path.join('pyjs', 'src', 'pyjs'),
                       'pyjd': 'pyjd'},
        data_files = data_files,
        license = "Apache Software License",
        platforms = ["any"],
        classifiers = [
            "Development Status :: 5 - Production/Stable",
            "Natural Language :: English",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Programming Language :: Python"
        ])

