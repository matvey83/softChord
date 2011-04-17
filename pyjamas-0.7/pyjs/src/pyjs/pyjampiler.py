#!/usr/bin/python
"""
@author: David Siroky (siroky@dasir.cz)

Copyright (C) 2009, David Siroky (siroky@dasir.cz)
Copyright (C) 2009, Luke Kenneth Casson Leighton <lkcl@lkcl.net>

Pyjampiler: a stand-alone python-to-javascript compiler, by David Siroky

"""
print 'pyjampiler loaded'

import os
import glob
import re
import shutil
from optparse import OptionParser

import pyjs.translator

if pyjs.pyjspth is None:
    BASE = os.path.dirname(__file__)
else:
    BASE = os.path.join(pyjs.pyjspth, "pyjs", "src", "pyjs")

PYJAMPILER_BASE = os.path.join(BASE, 'boilerplate')
BUILTIN_PATH = os.path.join(BASE, 'builtin')

#print "PYJAMPILER_BASE", PYJAMPILER_BASE

SYSTEM_MODULES_DIR = "system_modules"
TMP_DIR = "pyjampiler_tmp"

class Builder(object):
    def __init__(self):
        self.modules = []
        self.modules_source = []
        self.parse_options()
        self.run()

    def parse_options(self):
        parser = OptionParser()
        parser.add_option("-w", "--working-dir", dest="working_dir",
                          default=os.getcwd(),
                          help="root of your application")
        parser.add_option("-r", "--entry", dest="entry_module",
                          help="entry module of the application")
        parser.add_option("-e", "--exclude", dest="exclude",
                          help="exclude files (regular expression)")
        parser.add_option("-o", "--output", dest="output_file",
                          help="output file (e.g. \"app.js\")")
        parser.add_option("-d", "--debug", dest="debug", action="store_true",
                          default=False,
                          help="turn on debugging")
        (self.options, args) = parser.parse_args()
        if ((self.options.output_file is None) or (self.options.entry_module is None)):
            parser.error("need to specify entry module and output file")

        self.options.working_dir = os.path.abspath(self.options.working_dir)
        self.options.output_file = os.path.abspath(self.options.output_file)

    def __read_file(self, filename):
        f = file(filename, "r")
        buf = f.read()
        f.close()
        return buf

    def compile(self, src, module_name, base_dir=None):
        dst = os.path.join(self.options.working_dir, TMP_DIR, module_name + ".js")
        internal_ast = False
        compiler = pyjs.translator.import_compiler(internal_ast)
        pyjs.translator.translate(compiler, [src], dst, module_name,
                debug=self.options.debug,
                source_tracking=self.options.debug,
                line_tracking=self.options.debug,
                store_source=self.options.debug
              )
        self.modules.append(module_name)
        fr = file(dst, "r")
        self.modules_source.append(fr.read())
        fr.close()

    def compile_system_modules(self):
        # check if the system modules are present in the current direcoty
        if os.path.isdir(SYSTEM_MODULES_DIR):
            modules_dir = os.path.abspath(SYSTEM_MODULES_DIR)
        else:
            modules_dir = os.path.join(PYJAMPILER_BASE, SYSTEM_MODULES_DIR)

        for module_filename in glob.glob(os.path.join(modules_dir, "*.py")):
            module_name = os.path.basename(module_filename)[:-3]
            self.compile(module_filename, module_name, modules_dir)

    def compile_application(self):
        # compile application
        for dirname, subdirs, files in os.walk(self.options.working_dir):
            # put __init__.py at the begining
            if "__init__.py" in files:
                files.remove("__init__.py")
                files.insert(0, "__init__.py")

            for filename in files:
                filename = os.path.join(dirname, filename)
                based_filename = filename[len(self.options.working_dir)+1:]

                if not filename.endswith(".py"):
                    continue
                if self.options.exclude and \
                   re.match(self.options.exclude, based_filename):
                    continue

                if based_filename.endswith("__init__.py"):
                    module_name = os.path.dirname(based_filename)
                else:
                    module_name = based_filename[:-3] # cut ".py"
                module_name = module_name.replace(os.sep, ".")

                print "%s (%s)" % (module_name, based_filename)
                self.compile(based_filename, module_name, self.options.working_dir)

    def clear_tmp(self):
        tmp_dir = os.path.join(self.options.working_dir, TMP_DIR)
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.mkdir(tmp_dir)

    def run(self):
        self.clear_tmp()

        self.compile_system_modules()
        self.compile_application()

        # application template
        tmpl = self.__read_file(os.path.join(PYJAMPILER_BASE, 
                        "pyjampiler_wrapper.js.tmpl"))

        available_modules = repr(self.modules)
        _pyjs = self.__read_file(os.path.join(BUILTIN_PATH, 
                        "public/_pyjs.js")) # core pyjs functions
        modules_source = "\n\n".join(self.modules_source)

        fapp = file(os.path.join(self.options.working_dir,
                                self.options.output_file), "w")
        fapp.write(tmpl % {"available_modules": available_modules,
                          "_pyjs": _pyjs,
                          "modules_source": modules_source,
                          "entry_module": self.options.entry_module})
        fapp.close()

if __name__ == "__main__":
    Builder()

