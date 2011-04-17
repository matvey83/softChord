#!/usr/bin/env python

import PyV8

import os
import sys
import compiler

from os.path import join, dirname, basename, abspath
from optparse import OptionParser

usage = """
  usage: %prog [options] <application module name or path>
"""


currentdir = abspath(dirname(__file__))
pyjspth = abspath(join(dirname(__file__), ".."))
sys.path = [(join(pyjspth, "pyjs", "src"))] + sys.path

import pyjs

pyjs.pyjspth = pyjspth
pyjs.path += [os.path.join(pyjspth, 'library'),
            os.path.join(pyjspth, 'addons'),
]

#currentdir = abspath(dirname(dirname(__file__)))
#builddir = abspath("..")
#sys.path = [(join(builddir, "pyjs", "src"))] + sys.path
#print sys.path

#app_library_dirs = [
#    currentdir,
#    join(builddir, "library/builtins"),
#    join(builddir, "library"),
#    join(builddir, "addons")]
 
def tostrlist(l):
    l = map(lambda x: "'%s'" % x, l)
    return "[%s]" % ', '.join(l)

class FileWrapper(object):
    def __init__(self, fname, mode):
        self.f = open(fname, mode)

    def seek(self, seekto=None):
        if seekto is None:
            return self.f.seek()
        return self.f.seek(seekto)

    def close(self):
        return self.f.close()

    def write(self, bytes):
        return self.f.write(bytes)

    def read(self, bytes=None):
        if bytes is None:
            return self.f.read()
        return self.f.read(bytes)

# Create a python class to be used in the context
class Global(PyV8.JSClass):
    def pyv8_open(self, fname, mode):
        return FileWrapper(fname, mode)

    def pyv8_print_fn(self, arg):
        print arg

    def pyv8_import_module(self, parent_name, module_name):
        #print "pyv8_import_module", parent_name, module_name
        exec "import " + module_name
        return locals()[module_name]
    
    def pyv8_load(self, modules):
        for i in range(len(modules)):
            fname = modules[i]
            #print "pyv8_load", fname
            fp = open(fname, 'r')
            txt = fp.read()
            fp.close()

            x = self.__context__.eval(txt)




import os
from pyjs import linker
from pyjs import translator
from pyjs import util
from optparse import OptionParser

PLATFORM='pyv8'

APP_TEMPLATE = """
var $wnd = new Object();
$wnd.document = new Object();
var $doc = $wnd.document;
var $moduleName = "%(app_name)s";
var $pyjs = new Object();
$pyjs.__modules__ = {};
$pyjs.modules = {};
$pyjs.modules_hash = {};
$pyjs.available_modules = %(available_modules)s;
$pyjs.loaded_modules = {};
$pyjs.options = new Object();
$pyjs.options.set_all = function (v) {
    $pyjs.options.arg_ignore = v;
    $pyjs.options.arg_count = v;
    $pyjs.options.arg_is_instance = v;
    $pyjs.options.arg_instance_type = v;
    $pyjs.options.arg_kwarg_dup = v;
    $pyjs.options.arg_kwarg_unexpected_keyword = v;
    $pyjs.options.arg_kwarg_multiple_values = v;
};
$pyjs.options.set_all(true);
$pyjs.trackstack = [];
$pyjs.track = {module:'__main__', lineno: 1};
$pyjs.trackstack.push($pyjs.track);
$pyjs.__last_exception_stack__ = null;
$pyjs.__last_exception__ = null;

/*
 * prepare app system vars
 */
$pyjs.platform = 'pyv8';
$pyjs.appname = '%(app_name)s';
$pyjs.loadpath = './';

pyv8_load(%(module_files)s);

pyv8_load(%(js_lib_files)s);

/* late static js libs */

%(late_static_js_libs)s


//try {
    $pyjs.loaded_modules['pyjslib']('pyjslib');
    $pyjs.loaded_modules['pyjslib'].___import___('%(app_name)s', '%(app_name)s', '__main__');
//} catch(exception)
//{
//    var fullMessage = exception.name + ': ' + exception.message;
//    var uri = exception.fileName;
//    //var stack = exception.stack;
//    var line = exception.lineNumber;
//    fullMessage += "\\n at " + uri + ": " + line;
//    print (fullMessage );
//    //print (stack.toString() );
//}
"""

class PyV8Linker(linker.BaseLinker):
    """PyV8 linker, which links together files by using the
    load function of the spidermonkey shell."""

    # we derive from mozilla
    platform_parents = {
        PLATFORM:['mozilla', 'array_extras']
        }

    def __init__(self, *args, **kwargs):
        kwargs['platforms'] = [PLATFORM]
        super(PyV8Linker, self).__init__(*args, **kwargs)

    def visit_start(self):
        super(PyV8Linker, self).visit_start()
        self.js_libs.append('_pyjs.js')
        self.merged_public = set()

    def merge_resources(self, dir_name):
        """find the absolute paths of js includes"""
        if not self.js_libs or dir_name in self.merged_public:
            return
        public_folder = os.path.join(dir_name, 'public')
        if not os.path.isdir(public_folder):
            return
        for i, js_lib in enumerate(self.js_libs):
            p = os.path.join(public_folder, js_lib)
            if os.path.isfile(p):
                self.js_libs[i] = p

    def visit_end(self):

        def static_code(libs, msg = None):
            code = []
            for lib in libs:
                fname = lib
                if not os.path.isfile(fname):
                    fname = os.path.join(self.output, lib)
                if not os.path.isfile(fname):
                    raise RuntimeError('File not found %r' % lib)
                if fname[len_ouput_dir:] == self.output:
                    name = fname[len_ouput_dir:]
                else:
                    name = os.path.basename(lib)
                if not msg is None:
                    code.append("/* start %s: %s */" % (msg, name))
                f = file(fname)
                code.append(f.read())
                if not msg is None:
                    code.append("/* end %s */" % (name,))
                self.remove_files[fname] = True
                fname = fname.split('.')
                if fname[-2] == '__%s__' % platform_name:
                    del fname[-2]
                    fname = '.'.join(fname)
                    if os.path.isfile(fname):
                        self.remove_files[fname] = True
            return "\n".join(code)

        done = self.done[PLATFORM]

        # locals - go into template via locals()
        module_files=tostrlist(done)
        #print "module_files", module_files
        js_lib_files=tostrlist(self.js_libs)
        early_static_js_libs=str(self.js_libs)[1:-1]
        late_static_js_libs = [] + self.late_static_js_libs
        late_static_js_libs = static_code(late_static_js_libs, "javascript lib")

        app_name = self.top_module
        available_modules = self.visited_modules[PLATFORM]

        self.out_file_mod = os.path.join(self.output, self.top_module + '.js')
        out_file = open(self.out_file_mod , 'w')
        out_file.write(APP_TEMPLATE % locals())
        out_file.close()

def build_script():
    usage = """
    usage: %prog [options] module_name
    """
    parser = OptionParser(usage = usage)
    translator.add_compile_options(parser)

    parser.add_option(
        "--dynamic",
        dest="unlinked_modules",
        action="append",
        help="regular expression for modules that will not be linked and thus loaded dynamically"
        )

    # override the default because we want print
    parser.set_defaults(print_statements=True)
    linker.add_linker_options(parser)
    options, args = parser.parse_args()
    if len(args) == 0:
        parser.error("incorrect number of arguments")

    pyjs.path = ["."] + pyjs.path
    #top_module = args[0]
    for d in options.library_dirs:
        pyjs.path.append(os.path.abspath(d))

    print "paths:", pyjs.path

    translator_arguments=dict(
        debug=options.debug,
        print_statements = options.print_statements,
        function_argument_checking=options.function_argument_checking,
        attribute_checking=options.attribute_checking,
        source_tracking=options.source_tracking,
        line_tracking=options.line_tracking,
        store_source=options.store_source,
        inline_code = options.inline_code,
        operator_funcs = options.operator_funcs,
        number_classes = options.number_classes,
        )

    l = PyV8Linker(args, #[top_module],
                           output=options.output,
                           platforms=[PLATFORM],
                           path=pyjs.path,
                           compiler=compiler,
                           translator_arguments=translator_arguments)
    l()

    return l


def main():

    l = build_script()

    fp = open(l.out_file_mod, 'r')
    txt = fp.read()
    fp.close()

    #PyV8.debugger.enabled = True
    # create a context with an explicit global
    g = Global()
    ctxt = PyV8.JSContext(g)
    g.__context__ = ctxt
    # enter the context
    ctxt.enter()
    
    x = ctxt.eval(txt)


if __name__ == '__main__':
    main()

