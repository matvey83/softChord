#!/usr/bin/env python

import spidermonkey

import sys

from os.path import join, dirname, basename, abspath
from optparse import OptionParser

usage = """
  usage: %prog [options] <application module name or path>
"""

currentdir = abspath(dirname(dirname(__file__)))
builddir = abspath("..")
sys.path.append(join(builddir, "pyjs"))

import pyjs

file_name = None

app_library_dirs = [
    currentdir,
    join(builddir, "library/builtins"),
    join(builddir, "library"),
    join(builddir, "addons")]

cx = None

def pysm_print_fn(arg):
    print arg

def pysm_import_module(parent_name, module_name):
    if module_name == 'sys' or module_name == 'pyjslib':
        return
    if module_name == file_name: # HACK!  imported already
        return
    exec "import %s as _module" % module_name
    cx.add_global(module_name, _module)

def main():

    global file_name

    parser = OptionParser(usage = usage)
    pyjs.add_compile_options(parser)
    parser.add_option("-o", "--output",
        dest="output",
        help="File to which the generated javascript should be written")

    parser.add_option("-i", "--input",
        dest="input",
        help="File from which the generated javascript should be read")

    parser.set_defaults(\
        output = None,
        input = None,
    )
    (options, args) = parser.parse_args()

    file_name = args[0]
    if len(args) > 1:
        module_name = args[1]
    else:
        module_name = None

    debug = 0

    if options.input:
        txt = open(options.input, 'r').read()
    else:
        parser = pyjs.PlatformParser("platform", verbose=False)
        parser.setPlatform("pysm")

        if file_name.endswith(".py"):
            file_name = file_name[:-3]

        app_translator = pyjs.AppTranslator(
                app_library_dirs, parser,
                verbose = False,
                debug = options.debug,
                print_statements = options.print_statements,
                function_argument_checking = options.function_argument_checking,
                attribute_checking = options.attribute_checking,
                source_tracking = options.source_tracking,
                line_tracking = options.line_tracking,
                store_source = options.store_source,
        )
        app_libs, txt = app_translator.translate(file_name, debug=debug,
                                      library_modules=['_pyjs.js', 'sys', 'pyjslib'])

        template = """
var $pyjs = new Object();
$pyjs.modules = {};
$pyjs.modules_hash = {};
$pyjs.options = new Object();
$pyjs.options.set_all = function (v) {
    $pyjs.options.arg_ignore = v;
    $pyjs.options.arg_count = v;
    $pyjs.options.arg_is_instance = v;
    $pyjs.options.arg_instance_type = v;
    $pyjs.options.arg_kwarg_dup = v;
    $pyjs.options.arg_kwarg_unexpected_keyword = v;
    $pyjs.options.arg_kwarg_multiple_values = v;
}
$pyjs.options.set_all(true);
$pyjs.trackstack = [];
$pyjs.track = {module:'__main__', lineno: 1};
$pyjs.trackstack.push($pyjs.track);
%(app_libs)s


%(module)s

"""

        txt = template % {'app_libs': app_libs, 'module_name': file_name,
                          'module': txt}

        txt += "sys();\n" 
        txt += "pyjslib();\n" 
        txt += "%s();\n" % file_name

    if options.output:
        fp = open(options.output, 'w')
        fp.write(txt)
        fp.close()

    rt = spidermonkey.Runtime()
    global cx
    cx = rt.new_context()
    cx.add_global("pysm_print_fn", pysm_print_fn)
    cx.add_global("pysm_import_module", pysm_import_module)

    cx.execute(txt)

if __name__ == '__main__':
    main()
