# Copyright 2006 James Tauber and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
from types import StringType
import os
import copy
from cStringIO import StringIO
import re
try:
    from hashlib import md5
except:
    from md5 import md5
import logging
import compiler
from compiler.visitor import ASTVisitor

import pyjs

if pyjs.pyjspth is None:
    LIBRARY_PATH = os.path.abspath(os.path.dirname(__file__))
else:
    LIBRARY_PATH = os.path.join(pyjs.pyjspth, "pyjs", "src", "pyjs")

# this is the python function used to wrap native javascript
NATIVE_JS_FUNC_NAME = "JS"

# See http://www.quackit.com/javascript/javascript_reserved_words.cfm
JavaScript_Reserved_Words = frozenset((
    'break',
    'case',
    'comment',
    'continue',
    'default',
    'delete',
    'do',
    'else',
    'export',
    'for',
    'function',
    'if',
    'import',
    'in',
    'label',
    'new',
    'return',
    'switch',
    'this',
    'typeof',
    'var',
    'void',
    'while',
    'with',
))

ECMAScipt_Reserved_Words = frozenset((
    'catch',
    'class',
    'const',
    'debugger',
    'enum',
    'extends',
    'finally',
    'super',
    'throw',
    'try',
))

Java_Keywords = frozenset((# (Reserved by JavaScript)
    'abstract',
    'boolean',
    'byte',
    'char',
    'double',
    'false',
    'final',
    'float',
    'goto',
    'implements',
    'instanceOf',
    'int',
    'interface',
    'long',
    'native',
    'null',
    'package',
    'private',
    'protected',
    'public',
    'short',
    'static',
    'synchronized',
    'throws',
    'transient',
    'true',
))

Other_JavaScript_Keywords = frozenset((
    'Anchor',
    'Area',
    'Array',
    'Boolean',
    'Button',
    'Checkbox',
    'Date',
    'Document',
    'Element',
    'FileUpload',
    'Form',
    'Frame',
    'Function',
    'Hidden',
    'History',
    'Image',
    'Infinity',
    'JavaArray',
    'JavaClass',
    'JavaObject',
    'JavaPackage',
    'Link',
    'Location',
    'Math',
    'MimeType',
    'NaN',
    'Navigator',
    'Number',
    'Object',
    'Option',
    'Packages',
    'Password',
    'Plugin',
    'Radio',
    'RegExp',
    'Reset',
    'Select',
    'String',
    'Submit',
    'Text',
    'Textarea',
    'Window',
    'alert',
    'arguments',
    'assign',
    'blur',
    'callee',
    'caller',
    'captureEvents',
    'clearInterval',
    'clearTimeout',
    'close',
    'closed',
    'confirm',
    'constructor',
    'defaultStatus',
    'document',
    'escape',
    'eval',
    'find',
    'focus',
    'frames',
    'getClass',
    'history',
    'home',
    'innerHeight',
    'innerWidth',
    'isFinite',
    'isNan',
    'java',
    'length',
    'location',
    'locationbar',
    'menubar',
    'moveBy',
    'moveTo',
    'name',
    'navigate',
    'navigator',
    'netscape',
    'onBlur',
    'onError',
    'onFocus',
    'onLoad',
    'onUnload',
    'open',
    'opener',
    'outerHeight',
    'outerWidth',
    'pageXoffset',
    'pageYoffset',
    'parent',
    'parseFloat',
    'parseInt',
    'personalbar',
    'print',
    'prompt',
    'prototype',
    'ref',
    'releaseEvents',
    'resizeBy',
    'resizeTo',
    'routeEvent',
    'scroll',
    'scrollBy',
    'scrollTo',
    'scrollbars',
    'self',
    'setInterval',
    'setTimeout',
    'status',
    'statusbar',
    'stop',
    'sun',
    'taint',
    'toString',
    'toolbar',
    'top',
    'unescape',
    'untaint',
    'unwatch',
    'valueOf',
    'watch',
    'window',
))

PYJSLIB_BUILTIN_FUNCTIONS=frozenset((
    "__import__",
    "abs",
    "all",
    "any",
    "bool",
    "callable",
    "chr",
    "cmp",
    "delattr",
    "dir",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "getattr",
    "hasattr",
    "hash",
    "hex",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "map",
    "max",
    "min",
    "oct",
    "open",
    "ord",
    "pow",
    "range",
    "reduce",
    "repr",
    "reversed",
    "round",
    "setattr",
    "sorted",
    "staticmethod",
    "str",
    "sum",
    "super",
    "type",
    "xrange",
    "zip",
    ))

PYJSLIB_BUILTIN_CLASSES=[
    "ArithmeticError",
    "AttributeError",
    "BaseException",
    "Exception",
    "GeneratorExit",
    "ImportError",
    "IndexError",
    "KeyError",
    "LookupError",
    "NameError",
    "NotImplemented",   # is in fact an instance
    "NotImplementedError",
    "NotImplementedType",
    "RuntimeError",
    "StandardError",
    "StopIteration",
    "TypeError",
    "ValueError",
    "ZeroDivisionError",

    "dict",
    "frozenset",
    "int",
    "list",
    "long",
    "object",
    "property",
    "set",
    "tuple",
    ]

PYJSLIB_BUILTIN_MAPPING = {\
    'True' : 'true',
    'False': 'false',
    'None': 'null',
}

SCOPE_KEY = 0

BIND_TYPES_NUMERIC = {
    "static": 0,
    "bound": 1,
    "class": 2
  }

# Variable names that should be remapped in functions/methods
# arguments -> arguments_
# arguments_ -> arguments__
# etc.
# arguments is one of Other_JavaScript_Keywords, but is used 
# in function/method initialization and therefore forbidden
pyjs_vars_remap_names = ['arguments', 
                        'final', 'char'] # to pass lint
pyjs_vars_remap = {}
for a in pyjs_vars_remap_names:
    pyjs_vars_remap[a] = '$$' + a
for a in JavaScript_Reserved_Words:
    pyjs_vars_remap[a] = '$$' + a
for a in ECMAScipt_Reserved_Words:
    pyjs_vars_remap[a] = '$$' + a

# Attributes that should be remapped in classes
pyjs_attrib_remap_names = [\
    'prototype', 'call', 'apply', 'constructor',
    # Specifically for Chrome, which doesn't set the name attribute of a _function_
    # http://code.google.com/p/chromium/issues/detail?id=12871
    'name',
    # collisions between javascript/python
    'split', 'replace',
]
pyjs_attrib_remap = {}
for a in pyjs_attrib_remap_names:
    pyjs_attrib_remap[a] = '$$' + a
for a in JavaScript_Reserved_Words:
    pyjs_attrib_remap[a] = '$$' + a
for a in ECMAScipt_Reserved_Words:
    pyjs_attrib_remap[a] = '$$' + a


# pass in the compiler module (lib2to3 pgen or "standard" python one)
# and patch transformer. see http://bugs.python.org/issue6978
def monkey_patch_broken_transformer(compiler):

    if compiler.__name__ != 'compiler':
        return # don't patch pgen.lib2to3.compiler.transformer!

    # assumes that compiler.transformer imports all these
    extractLineNo = compiler.transformer.extractLineNo
    token = compiler.transformer.token
    symbol = compiler.transformer.symbol
    Subscript = compiler.transformer.Subscript 
    Tuple = compiler.transformer.Tuple 
    Ellipsis = compiler.transformer.Ellipsis 
    Sliceobj = compiler.transformer.Sliceobj 

    # Bugfix compiler.transformer.Transformer.com_subscriptlist
    def com_subscriptlist(self, primary, nodelist, assigning):
        # slicing:      simple_slicing | extended_slicing
        # simple_slicing:   primary "[" short_slice "]"
        # extended_slicing: primary "[" slice_list "]"
        # slice_list:   slice_item ("," slice_item)* [","]

        # backwards compat slice for '[i:j]'
        if len(nodelist) == 2:
            sub = nodelist[1]
            if (sub[1][0] == token.COLON or \
                            (len(sub) > 2 and sub[2][0] == token.COLON)) and \
                            sub[-1][0] != symbol.sliceop:
                return self.com_slice(primary, sub, assigning)

        subscripts = []
        for i in range(1, len(nodelist), 2):
            subscripts.append(self.com_subscript(nodelist[i]))
        if len(nodelist) > 2:
            tulplesub = [sub for sub in subscripts \
                            if not (isinstance(sub, Ellipsis) or \
                            isinstance(sub, Sliceobj))]
            if len(tulplesub) == len(subscripts):
                subscripts = [Tuple(subscripts)]
        return Subscript(primary, assigning, subscripts,
                         lineno=extractLineNo(nodelist))

    compiler.transformer.Transformer.com_subscriptlist = com_subscriptlist

debug_options = {}
speed_options = {}
pythonic_options = {}

re_return = re.compile(r'\breturn\b')
class __Pyjamas__(object):
    console = "console"

    def JS(self, translator, node):
        if len(node.args) != 1:
            raise TranslationError(
                "JS function requires one argument",
                node.node)
        if (     isinstance(node.args[0], translator.ast.Const)
             and isinstance(node.args[0].value, str)
           ):
            translator.ignore_debug = True
            return node.args[0].value, not re_return.search(node.args[0].value) is None
        else:
            raise TranslationError(
                "JS function only support constant strings",
                node.node)

    def wnd(self, translator, node):
        if len(node.args) != 0:
            raise TranslationError(
                "wnd function doesn't support arguments",
                node.node)
        translator.ignore_debug = True
        return '$wnd', False

    def doc(self, translator, node):
        if len(node.args) != 0:
            raise TranslationError(
                "doc function doesn't support arguments",
                node.node)
        translator.ignore_debug = True
        return '$doc', False

    def jsinclude(self, translator, node):
        if len(node.args) != 1:
            raise TranslationError(
                "jsinclude function requires one argument",
                node.node)
        if (     isinstance(node.args[0], translator.ast.Const)
             and isinstance(node.args[0].value, str)
           ):
            try:
                data = open(node.args[0].value, 'r').read()
            except IOError, e:
                raise TranslationError(
                    "Cannot include file '%s': %s" % (node.args[0].value, e))
            translator.ignore_debug = True
            return data, False
        else:
            raise TranslationError(
                "jsinclude function only supports constant strings",
                node.node)

    def jsimport(self, translator, node):
        # jsimport(path, mode, location)
        # mode = [default|static|dynamic] (default: depends on build argument -m)
        # location = [early|middle|late] (only relevant for static)
        if len(node.args) == 0 or len(node.args) > 3:
            raise TranslationError(
                "jsimport function requires at least one, and at most three arguments",
                node.node)
        for arg in node.args:
            if not isinstance(arg, translator.ast.Const):
                raise TranslationError(
                    "jsimport function only supports constant arguments",
                node.node)
        if not isinstance(node.args[0].value, str):
            raise TranslationError(
                "jsimport path argument must be a string",
                node.node)
        path = node.args[0].value
        if len(node.args) < 2:
            mode = 'default'
        else:
            if isinstance(node.args[1].value, str):
                mode = node.args[1].value
            else:
                raise TranslationError(
                    "jsimport path argument must be a string",
                    node.node)
            if not mode in ['default', 'static', 'dynamic']:
                raise TranslationError(
                    "jsimport mode argument must be default, static or dynamic",
                node.node)
        if len(node.args) < 3:
            location = 'middle'
        else:
            if isinstance(node.args[2].value, str):
                location = node.args[2].value
            else:
                raise TranslationError(
                    "jsimport path argument must be a string",
                    node.node)
            if not location in ['early', 'middle', 'late']:
                raise TranslationError(
                    "jsimport location argument must be early, middle or late",
                node.node)
        translator.add_imported_js(path, mode, location)
        translator.ignore_debug = True
        return '', False

    def debugger(self, translator, node):
        if len(node.args) != 0:
            raise TranslationError(
                "debugger function doesn't support arguments",
                node.node)
        translator.ignore_debug = True
        return 'debugger', False

    def setCompilerOptions(self, translator, node):
        global speed_options, pythonic_options
        for arg in node.args:
            if not isinstance(arg, translator.ast.Const) or not isinstance(arg.value, str):
                raise TranslationError(
                    "jsimport function only supports constant string arguments",
                node.node)
            option = arg.value
            if translator.decorator_compiler_options.has_key(option):
                for var, val in translator.decorator_compiler_options[option]:
                    setattr(translator, var, val)
            elif option == "Speed":
                for var in speed_options:
                    setattr(translator, var, speed_options[var])
            elif option == "Strict":
                for var in pythonic_options:
                    setattr(translator, var, pythonic_options[var])
            else:
                raise TranslationError(
                    "setCompilerOptions invalid option '%s'" % option,
                    node.node)
        translator.ignore_debug = True
        return '', False

    def INT(self, translator, node):
        if len(node.args) != 1:
            raise TranslationError(
                "INT function requires one argument",
                node.node)
        expr = translator.expr(node.args[0], None)
        opt_var = translator.decorator_compiler_options['NumberClasses'][0][0]
        if  getattr(translator, opt_var):
            return "new pyjslib['int'](%s)" % expr, False
        return expr, False


__pyjamas__ = __Pyjamas__()

# This is taken from the django project.
# Escape every ASCII character with a value less than 32.
JS_ESCAPES = (
    ('\\', r'\x5C'),
    ('\'', r'\x27'),
    ('"', r'\x22'),
    ('>', r'\x3E'),
    ('<', r'\x3C'),
    ('&', r'\x26'),
    (';', r'\x3B')
    ) + tuple([('%c' % z, '\\x%02X' % z) for z in range(32)])

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in JS_ESCAPES:
        value = value.replace(bad, good)
    return value


class YieldVisitor(ASTVisitor):
    has_yield = False
    def visitYield(self, node, *args):
        self.has_yield = True

class GeneratorExitVisitor(YieldVisitor):
    has_yield = False
    def visitReturn(self, node, *args):
        self.has_yield = True

class Klass:

    klasses = {}

    def __init__(self, name, name_scope):
        self.name = name
        self.name_scope = name_scope
        self.klasses[name] = self
        self.functions = set()

    def set_base(self, base_name):
        self.base = self.klasses.get(base_name)

    def add_function(self, function_name):
        self.functions.add(function_name)


class TranslationError(Exception):
    def __init__(self, msg, node, module_name=''):
        if node:
            lineno = node.lineno
        else:
            lineno = "Unknown"
        self.msg = msg
        self.node = node
        self.module_name = module_name
        self.lineno = lineno
        Exception.__init__(self, "%s line %s:\n%s\n%s" % (module_name, lineno, msg, node))

    def __str__(self):
        return self.args[0]

def strip_py(name):
    return name

def mod_var_name_decl(module_name):
    """ function to get the last component of the module e.g.
        pyjamas.ui.DOM into the "namespace".  i.e. doing
        "import pyjamas.ui.DOM" actually ends up with _two_
        variables - one pyjamas.ui.DOM, the other just "DOM".
        but "DOM" is actually local, hence the "var" prefix.

        for PyV8, this might end up causing problems - we'll have
        to see: gen_mod_import and mod_var_name_decl might have
        to end up in a library-specific module, somewhere.
    """
    name = module_name.split(".")
    if len(name) == 1:
        return ''
    child_name = name[-1]
    return "var %s = %s;\n" % (child_name, module_name)

class Translator:

    decorator_compiler_options = {\
        'Debug': [('debug', True)],
        'noDebug': [('debug', False)],
        'PrintStatements': [('print_statements', True)],
        'noPrintStatements': [('print_statements', False)],
        'FunctionArgumentChecking': [('function_argument_checking', True)],
        'noFunctionArgumentChecking': [('function_argument_checking', False)],
        'AttributeChecking': [('attribute_checking', True)],
        'noAttributeChecking': [('attribute_checking', False)],
        'BoundMethods': [('bound_methods', True)],
        'noBoundMethods': [('bound_methods', False)],
        'Descriptors': [('descriptors', True)],
        'noDescriptors': [('descriptors', False)],
        'SourceTracking': [('source_tracking', True)],
        'noSourceTracking': [('source_tracking', False)],
        'LineTracking': [('line_tracking', True)],
        'noLineTracking': [('line_tracking', False)],
        'StoreSource': [('store_source', True)],
        'noStoreSource': [('store_source', False)],
        'noInlineBool': [('inline_bool', False)],
        'InlineBool': [('inline_bool', True)],
        'noInlineLen': [('inline_len', False)],
        'InlineLen': [('inline_len', True)],
        'noInlineEq': [('inline_eq', False)],
        'InlineEq': [('inline_eq', True)],
        'noInlineCmp': [('inline_cmp', False)],
        'InlineCmp': [('inline_cmp', True)],
        'noInlineGetItem': [('inline_getitem', False)],
        'InlineGetItem': [('inline_getitem', True)],
        'noInlineCode': [('inline_bool', False),('inline_len', False),('inline_eq', False), ('inline_cmp', False), ('inline_getitem', False)],
        'InlineCode': [('inline_bool', True),('inline_len', True),('inline_eq', True), ('inline_cmp', True), ('inline_getitem', True)],
        'noOperatorFuncs': [('operator_funcs', False)],
        'OperatorFuncs': [('operator_funcs', True)],
        'noNumberClasses': [('number_classes', False)],
        'NumberClasses': [('number_classes', True)],
    }

    def __init__(self, compiler,
                 module_name, module_file_name, src, mod, output,
                 dynamic=0, findFile=None,
                 debug = False,
                 print_statements=True,
                 function_argument_checking=True,
                 attribute_checking=True,
                 bound_methods=True,
                 descriptors=True,
                 source_tracking=True,
                 line_tracking=True,
                 store_source=True,
                 inline_code=True,
                 operator_funcs=True,
                 number_classes=True,
                ):

        monkey_patch_broken_transformer(compiler)

        self.compiler = compiler
        self.ast = compiler.ast
        self.js_module_name = self.jsname("variable", module_name)
        if module_name:
            self.module_prefix = module_name + "."
        else:
            self.module_prefix = ""
        self.module_name = module_name
        src = src.replace("\r\n", "\n")
        src = src.replace("\n\r", "\n")
        src = src.replace("\r",   "\n")
        self.src = src.split("\n")

        self.output = output
        self.dynamic = dynamic
        self.findFile = findFile
        # compile options
        self.debug = debug
        self.ignore_debug = False
        self.print_statements = print_statements
        self.function_argument_checking = function_argument_checking
        self.attribute_checking = attribute_checking
        self.bound_methods = bound_methods
        self.descriptors = descriptors
        self.source_tracking = source_tracking
        self.line_tracking = line_tracking
        self.store_source = store_source
        self.inline_bool = inline_code
        self.inline_len = inline_code
        self.inline_eq = inline_code
        self.inline_cmp = inline_code
        self.inline_getitem = inline_code
        self.operator_funcs = operator_funcs
        self.number_classes = number_classes
        if self.number_classes:
            self.operator_funcs = True

        self.imported_modules = []
        self.imported_js = []
        self.is_class_definition = False
        self.local_prefix = None
        self.track_lines = {}
        self.stacksize_depth = 0
        self.option_stack = []
        self.lookup_stack = [{}]
        self.indent_level = 0
        self.__unique_ids__ = {}
        self.try_depth = -1
        self.is_generator = False
        self.generator_states = []
        self.state_max_depth = len(self.generator_states)
        self.constant_int = {}
        self.constant_long = {}
        self.top_level = True
        PYJSLIB_BUILTIN_MAPPING['__file__'] = "'%s'" % module_file_name

        print >>self.output, self.spacing() + "/* start module: %s */" % module_name
        if not '.' in module_name:
            #if module_name != self.jsname(module_name):
            #    raise TranslationError(
            #        "reserved word used for top-level module %r" % module_name,
            #        mod, self.module_name)
            print >>self.output, self.spacing() + 'var %s;' % self.js_module_name
            self.parent_module_name = None
        else:
            self.parent_module_name = '.'.join(module_name.split('.')[:-1])
        if module_file_name.endswith('__init__.py'):
            self.import_context = "'%s'" % module_name
        elif self.parent_module_name:
            self.import_context = "'%s'" % self.parent_module_name
        else:
            self.import_context = "null"

        print >>self.output, self.indent() + "$pyjs.loaded_modules['%s'] = function (__mod_name__) {" % module_name
        print >>self.output, self.spacing() + "if($pyjs.loaded_modules['%s'].__was_initialized__) return $pyjs.loaded_modules['%s'];"% (module_name, module_name)
        if self.parent_module_name:
            print >>self.output, self.spacing() + "if(typeof $pyjs.loaded_modules['%s'] == 'undefined' || !$pyjs.loaded_modules['%s'].__was_initialized__) pyjslib['___import___']('%s', null);"% (self.parent_module_name, self.parent_module_name, self.parent_module_name)
        parts = self.js_module_name.split('.')
        if len(parts) > 1:
            print >>self.output, self.spacing() + 'var %s = $pyjs.loaded_modules["%s"];' % (parts[0], module_name.split('.')[0])
        print >>self.output, self.spacing() + '%s = $pyjs.loaded_modules["%s"];' % (self.js_module_name, module_name)

        print >>self.output, self.spacing() + self.js_module_name+".__was_initialized__ = true;"
        print >>self.output, self.spacing() + "if ((__mod_name__ === null) || (typeof __mod_name__ == 'undefined')) __mod_name__ = '%s';" % (module_name)
        lhs = "%s.__name__" % self.js_module_name
        self.add_lookup('builtin', '__name__', lhs)
        print >>self.output, self.spacing() + "var __name__ = %s = __mod_name__;" % (lhs)
        if self.source_tracking:
            print >> self.output, self.spacing() + "%s.__track_lines__ = new Array();" % self.js_module_name
        name = module_name.split(".")
        if len(name) > 1:
            jsname = self.jsname("variable", name[-1])
            print >>self.output, self.spacing() + "var %s = %s;" % (jsname, self.js_module_name)

        if self.attribute_checking and not module_name in ['sys', 'pyjslib']:
            attribute_checking = True
            print >>self.output, self.indent() + 'try {'
        else:
            attribute_checking = False

        save_output = self.output
        self.output = StringIO()

        mod.lineno = 1
        self.track_lineno(mod, True)
        for child in mod.node:
            self.has_js_return = False
            self.has_yield = False
            self.is_generator = False
            self.track_lineno(child)
            assert self.top_level
            if isinstance(child, self.ast.Function):
                self._function(child, None)
            elif isinstance(child, self.ast.Class):
                self._class(child)
            elif isinstance(child, self.ast.Import):
                self._import(child, None, True)
            elif isinstance(child, self.ast.From):
                self._from(child, None, True)
            elif isinstance(child, self.ast.Discard):
                self._discard(child, None)
            elif isinstance(child, self.ast.Assign):
                self._assign(child, None)
            elif isinstance(child, self.ast.AugAssign):
                self._augassign(child, None)
            elif isinstance(child, self.ast.If):
                self._if(child, None)
            elif isinstance(child, self.ast.For):
                self._for(child, None)
            elif isinstance(child, self.ast.While):
                self._while(child, None)
            elif isinstance(child, self.ast.Subscript):
                self._subscript_stmt(child, None)
            elif isinstance(child, self.ast.Global):
                self._global(child, None)
            elif isinstance(child, self.ast.Printnl):
               self._print(child, None)
            elif isinstance(child, self.ast.Print):
               self._print(child, None)
            elif isinstance(child, self.ast.TryExcept):
                self._tryExcept(child, None)
            elif isinstance(child, self.ast.TryFinally):
                self._tryFinally(child, None)
            elif isinstance(child, self.ast.Raise):
                self._raise(child, None)
            elif isinstance(child, self.ast.Stmt):
                self._stmt(child, None, True)
            elif isinstance(child, self.ast.AssAttr):
                self._assattr(child, None)
            elif isinstance(child, self.ast.AssName):
                self._assname(child, None)
            elif isinstance(child, self.ast.Slice):
                print >> self.output, self.spacing() + self._slice(child, None)
            else:
                raise TranslationError(
                    "unsupported type (in __init__)",
                    child, self.module_name)

        captured_output = self.output.getvalue()
        self.output = save_output
        if self.source_tracking and self.store_source:
            for l in self.track_lines.keys():
                print >> self.output, self.spacing() + '''%s.__track_lines__[%d] = "%s";''' % (self.js_module_name, l, self.track_lines[l].replace('"', '\"'))
        print >> self.output, self.local_js_vars_decl([])
        if captured_output.find("@CONSTANT_DECLARATION@") >= 0:
            captured_output = captured_output.replace("@CONSTANT_DECLARATION@", self.constant_decl())
        else:
            print >> self.output, self.constant_decl()
        print >> self.output, captured_output,

        if attribute_checking:
            print >> self.output, self.dedent() + "} catch ($pyjs_attr_err) {throw pyjslib['_errorMapping']($pyjs_attr_err);};"

        print >> self.output, self.spacing() + "return this;"
        print >> self.output, self.dedent() + "}; /* end %s */"  % module_name
        print >> self.output, "\n"
        print >> self.output, self.spacing() + "/* end module: %s */" % module_name
        print >> self.output, "\n"

        # print out the deps and check for wrong imports
        if self.imported_modules:
            print >> self.output, '/*'
            print >> self.output, 'PYJS_DEPS: %s' % self.imported_modules
            print >> self.output, '*/'

    def uniqid(self, prefix = ""):
        if not self.__unique_ids__.has_key(prefix):
            self.__unique_ids__[prefix] = 0
        self.__unique_ids__[prefix] += 1
        return "%s%d" % (prefix, self.__unique_ids__[prefix])

    def spacing(self):
        return "\t" * self.indent_level

    def indent(self):
        spacing = self.spacing()
        self.indent_level += 1
        return spacing

    def dedent(self):
        if self.indent_level == 0:
            raise TranslationError("Dedent error", None, self.module_name)
        self.indent_level -= 1
        return self.spacing()

    def push_options(self):
        self.option_stack.append((\
            self.debug, self.print_statements, self.function_argument_checking,
            self.attribute_checking, self.bound_methods, self.descriptors,
            self.source_tracking, self.line_tracking, self.store_source,
            self.inline_bool, self.inline_eq, self.inline_len, self.inline_cmp, self.inline_getitem,
            self.operator_funcs, self.number_classes,
        ))
    def pop_options(self):
        (\
            self.debug, self.print_statements, self.function_argument_checking,
            self.attribute_checking, self.bound_methods, self.descriptors,
            self.source_tracking, self.line_tracking, self.store_source,
            self.inline_bool, self.inline_eq, self.inline_len, self.inline_cmp, self.inline_getitem,
            self.operator_funcs, self.number_classes,
        ) = self.option_stack.pop()

    def parse_decorators(self, node, funcname, current_class = None, 
                          is_method = False, bind_type = None):
        if node.decorators is None:
            return False, False, '%s'
        self.push_lookup()
        self.add_lookup('variable', '%s', '%s')
        code = '%s'
        staticmethod = False
        classmethod = False
        lineno=node.lineno

        if is_method:
            bind_type = bind_type or "bound"

        def add_callfunc(code, d, generic=True):
            tnode = self.ast.CallFunc(d, [self.ast.Name('%s')],
                                      star_args=None,
                                      dstar_args=None,
                                      lineno=lineno)
            code = code % self._callfunc_code(tnode, None)

            if is_method and (bind_type == "bound") and generic:
                try:
                    bind_type_num = BIND_TYPES_NUMERIC[bind_type]
                except KeyError:
                    raise TranslationError("Unknown bind type: %s" % bind_type, node)
                code = "$pyjs__decorated_method($cls_instance, '%(method_name)s', %(code)s, %(bind_type)s)" % \
                        {
                          "method_name": node.name,
                          "code": code,
                          "bind_type": bind_type_num
                        }

            return code

        for d in node.decorators:
            if isinstance(d, self.ast.Getattr):
                if isinstance(d.expr, self.ast.Name):
                    if d.expr.name == 'compiler':
                        raise TranslationError(
                            "The @compiler decorator is deprecated. Use from __pyjamas__ import setCompilerOptions", node, self.module_name)
                    if d.attrname in ("setter", "getter", "deleter"):
                        code = add_callfunc(code, d, generic=False)
                    else:
                        code = add_callfunc(code, d)
                else:
                    code = add_callfunc(code, d)
            elif isinstance(d, self.ast.Name):
                if d.name == 'staticmethod':
                    staticmethod = True
                elif d.name == 'classmethod':
                    classmethod = True
                elif d.name == 'property':
                    code = add_callfunc(code, d, generic=False)
                else:
                    code = add_callfunc(code, d)
            else:
                raise TranslationError(
                    "Unsupported decorator '%s'" % d, node, self.module_name)

        self.pop_lookup()
        if code != '%s':
            code = code % "pyjslib['staticmethod'](%s)"
        return (staticmethod, classmethod, code)

    # Join an list into a variable with optional attributes
    def attrib_join(self, splitted):
        if not isinstance(splitted, list):
            raise TranslationError("Invalid splitted attr '%s'" % splitted)
        attr = []
        if splitted[0][0] in ["'", '"']:
            attr.append(splitted[0][1:-1])
        else:
            attr.append(splitted[0])
        for word in splitted[1:]:
            if word[0] in ["'", '"']:
                word = word[1:-1]
            if word in pyjs_attrib_remap:
               attr.append("'%s'" % pyjs_attrib_remap[word])
            elif word.find('(') >= 0:
                print 'attrib_join:', splitted, attr, word
                attr.append(word)
            else:
               attr.append("'%s'" % word)
        if len(attr) == 1:
            return attr[0]
        return "%s%s" % (attr[0], ('[' + "][".join(attr[1:]) + ']'))

    def vars_remap(self, word):
        if word in pyjs_vars_remap:
           return pyjs_vars_remap[word]
        return word

    # Map a word to a valid attribute
    def attrib_remap(self, word):
        attr = []
        words = word.split('.')
        if len(words) == 1:
            if word in pyjs_attrib_remap:
                return pyjs_attrib_remap[word]
            return word
        raise RuntimeError("attrib_remap %s" % words)

    def push_lookup(self, scope = None):
        if scope is None:
            scope = {}
        self.lookup_stack.append(scope)

    def pop_lookup(self):
        return self.lookup_stack.pop()

    def jsname(self, name_type, jsname):
        words = jsname.split('.')
        if name_type != 'builtin':
            words[0] = self.vars_remap(words[0])
        if len(words) == 0:
            return words[0]
        return self.attrib_join(words)

    def add_lookup(self, name_type, pyname, jsname, depth = -1):
        jsname = self.jsname(name_type, jsname)
        if self.local_prefix is not None:
            if jsname.find(self.local_prefix) != 0:
                jsname = self.jsname(name_type, "%s.%s" % (self.local_prefix, jsname))
        if self.lookup_stack[depth].has_key(pyname):
            name_type = self.lookup_stack[depth][pyname][0]
        if self.module_name != 'pyjslib' or pyname != 'int':
            self.lookup_stack[depth][pyname] = (name_type, pyname, jsname)
        return jsname

    def lookup(self, name):
        # builtin
        # import
        # class
        # function
        # variable
        name_type = None
        pyname = name
        jsname = None
        max_depth = depth = len(self.lookup_stack) - 1
        while depth >= 0:
            if self.lookup_stack[depth].has_key(name):
                name_type, pyname, jsname = self.lookup_stack[depth][name]
                break
            depth -= 1
        if depth < 0:
            if name in PYJSLIB_BUILTIN_FUNCTIONS:
                name_type = 'builtin'
                pyname = name
                jsname = self.jsname("variable", "pyjslib['%s']" % self.attrib_remap(name))
            elif name in PYJSLIB_BUILTIN_CLASSES:
                name_type = 'builtin'
                pyname = name
                if not self.number_classes:
                    if pyname in ['int', 'long']:
                        name = 'float_int'
                jsname = self.jsname("variable", "pyjslib['%s']" % self.attrib_remap(name))
            elif PYJSLIB_BUILTIN_MAPPING.has_key(name):
                name_type = 'builtin'
                pyname = name
                jsname = PYJSLIB_BUILTIN_MAPPING[name]
        return (name_type, pyname, jsname, depth, (name_type is not None) and (max_depth > 0) and (max_depth == depth))

    def scopeName(self, name, depth, local):
        if local:
            return name
        while depth >= 0:
            scopeName = self.lookup_stack[depth].get(SCOPE_KEY, None)
            if scopeName is not None:
                return scopeName + name
            depth -= 1
        return self.modpfx() + name

    def constant_decl(self):
        s = self.spacing()
        lines = []
        for name in self.constant_int:
            lines.append("%(s)svar $constant_int_%(name)s = new pyjslib['int'](%(name)s);" % locals())
        for name in self.constant_long:
            lines.append("%(s)svar $constant_long_%(name)s = new pyjslib['long'](%(name)s);" % locals())
        return "\n".join(lines)

    def local_js_vars_decl(self, ignore_py_vars):
        names = []
        for name in self.lookup_stack[-1].keys():
            nametype = self.lookup_stack[-1][name][0]
            pyname = self.lookup_stack[-1][name][1]
            jsname = self.lookup_stack[-1][name][2]
            if (     not jsname.find('[') >= 0
                 and not pyname in ignore_py_vars
                 and not nametype in ['__pyjamas__', '__javascript__', 'global']
               ):
                names.append(jsname)
        if len(names) > 0:
            return self.spacing() + "var %s;" % ','.join(names)
        return ''

    def add_imported_js(self, path, mode, location):
        self.imported_js.append((path, mode, location))

    def add_imported_module(self, importName):
        names = importName.split(".")
        if not importName in self.imported_modules:
            self.imported_modules.append(importName)
        if importName.endswith('.js'):
            return
        # Add all parent modules
        _importName = ''
        for name in names:
            _importName += name
            if not _importName in self.imported_modules:
                self.imported_modules.append(_importName)
            _importName += '.'

    __inline_bool_code_str = """\
((%(v)s=%(e)s) === null || %(v)s === false || %(v)s === 0 || %(v)s === '' ?
    false :
    (typeof %(v)s=='object'?
        (typeof %(v)s.__nonzero__=='function'?
            %(v)s.__nonzero__() :
            (typeof %(v)s.__len__=='function'?
                (%(v)s.__len__()>0 ?
                    true :
                    false) :
                true ) ) :
         true ) )"""
    __inline_bool_code_str = __inline_bool_code_str.replace("    ", "\t").replace("\n", "\n%(s)s")

    def inline_bool_code(self, e):
        if self.inline_bool:
            v = self.uniqid('$bool')
            self.add_lookup('variable', v, v)
            s = self.spacing()
            return self.__inline_bool_code_str % locals()
        return "pyjslib['bool'](%(e)s)" % locals()

    __inline_len_code_str1 = """((%(v)s=%(e)s) === null?%(zero)s:
    (typeof %(v)s.__array != 'undefined' ? %(v)s.__array.length:
        (typeof %(v)s.__len__ == 'function'?%(v)s.__len__():
            (typeof %(v)s.length != 'undefined'?%(v)s.length:
                pyjslib['len'](%(v)s)))))"""
    __inline_len_code_str1 = __inline_len_code_str1.replace("    ", "\t").replace("\n", "\n%(s)s")

    __inline_len_code_str2 = """((%(v)s=%(e)s) === null?%(zero)s:
    (typeof %(v)s.__array != 'undefined' ? new pyjslib['int'](%(v)s.__array.length):
        (typeof %(v)s.__len__ == 'function'?%(v)s.__len__():
            (typeof %(v)s.length != 'undefined'? new pyjslib['int'](%(v)s.length):
                pyjslib['len'](%(v)s)))))"""
    __inline_len_code_str2 = __inline_len_code_str2.replace("    ", "\t").replace("\n", "\n%(s)s")

    def inline_len_code(self, e):
        if self.inline_len:
            v = self.uniqid('$len')
            self.add_lookup('variable', v, v)
            zero = '0'
            s = self.spacing()
            if not self.number_classes:
                return self.__inline_len_code_str1 % locals()
            self.constant_int['0'] = 1
            zero = "$constant_int_0"
            return self.__inline_len_code_str2 % locals()
        return "pyjslib['len'](%(e)s)" % locals()

    __inline_eq_code_str = """((%(v1)s=%(e1)s)===(%(v2)s=%(e2)s)&&%(v1)s===null?true:
    (%(v1)s===null?false:(%(v2)s===null?false:
        ((typeof %(v1)s=='object'||typeof %(v1)s=='function')&&typeof %(v1)s.__cmp__=='function'?%(v1)s.__cmp__(%(v2)s) === 0:
            ((typeof %(v2)s=='object'||typeof %(v2)s=='function')&&typeof %(v2)s.__cmp__=='function'?%(v2)s.__cmp__(%(v1)s) === 0:
                %(v1)s==%(v2)s)))))"""
    __inline_eq_code_str = __inline_eq_code_str.replace("    ", "\t").replace("\n", "\n%(s)s")

    def inline_eq_code(self, e1, e2):
        if self.inline_eq and not self.number_classes:
            v1 = self.uniqid('$eq')
            v2 = self.uniqid('$eq')
            self.add_lookup('variable', v1, v1)
            self.add_lookup('variable', v2, v2)
            s = self.spacing()
            return self.__inline_eq_code_str % locals()
        return "pyjslib['op_eq'](%(e1)s, %(e2)s)" % locals()

    __inline_cmp_code_str = """((%(v1)s=%(e1)s)===(%(v2)s=%(e2)s)?0:
    (typeof %(v1)s==typeof %(v2)s && ((typeof %(v1)s == 'number')||(typeof %(v1)s == 'string')||(typeof %(v1)s == 'boolean'))?
        (%(v1)s == %(v2)s ? 0 : (%(v1)s < %(v2)s ? -1 : 1)):
        pyjslib['cmp'](%(v1)s, %(v2)s)))"""
    __inline_cmp_code_str = __inline_cmp_code_str.replace("    ", "\t").replace("\n", "\n%(s)s")

    def inline_cmp_code(self, e1, e2):
        if self.inline_cmp:
            v1 = self.uniqid('$cmp')
            v2 = self.uniqid('$cmp')
            self.add_lookup('variable', v1, v1)
            self.add_lookup('variable', v2, v2)
            s = self.spacing()
            return self.__inline_cmp_code_str % locals()
        return "pyjslib['cmp'](%(e1)s, %(e2)s)" % locals()

    __inline_getitem_code_str = """(typeof (%(v1)s=%(e)s).__array != 'undefined'?
    ((typeof %(v1)s.__array[%(v2)s=%(i)s]) != 'undefined'?%(v1)s.__array[%(v2)s]:
        %(v1)s.__getitem__(%(v2)s)): 
        %(v1)s.__getitem__(%(i)s))"""
    __inline_getitem_code_str = __inline_getitem_code_str.replace("    ", "\t").replace("\n", "\n%(s)s")

    def inline_getitem_code(self, e, i):
        if self.inline_getitem:
            v1 = self.uniqid('$')
            self.add_lookup('variable', v1, v1)
            v2 = self.uniqid('$')
            self.add_lookup('variable', v2, v2)
            s = self.spacing()
            return self.__inline_getitem_code_str % locals()
        return "%(e)s.__getitem__(%(i)s)" % locals()

    def md5(self, node):
        return md5(self.module_name + str(node.lineno) + repr(node)).hexdigest()

    def track_lineno(self, node, module=False):
        if self.source_tracking and node.lineno:
            if module:
                print >> self.output, self.spacing() + "$pyjs.track.module='%s';" % self.module_name
            if self.line_tracking:
                print >> self.output, self.spacing() + "$pyjs.track.lineno=%d;" % node.lineno
                #print >> self.output, self.spacing() + "if ($pyjs.track.module!='%s') debugger;" % self.module_name
            if self.store_source:
                self.track_lines[node.lineno] = self.get_line_trace(node)

    def track_call(self, call_code, lineno=None):
        if not self.ignore_debug and self.debug and len(call_code.strip()) > 0:
            dbg = self.uniqid("$pyjs_dbg_")
            mod = self.module_name
            call_code = """\
(function(){\
var %(dbg)s_retry = 0;
try{var %(dbg)s_res=%(call_code)s;}catch(%(dbg)s_err){
    if (%(dbg)s_err.__name__ != 'StopIteration') {
        var save_stack = $pyjs.__last_exception_stack__;
        sys.save_exception_stack();
        var $pyjs_msg = "";

        try {
            $pyjs_msg = "\\n" + sys.trackstackstr();
        } catch (s) {};
        $pyjs.__last_exception_stack__ = save_stack;
        if ($pyjs_msg !== $pyjs.debug_msg) {
            pyjslib['debugReport']("Module %(mod)s at line %(lineno)s :\\n" + %(dbg)s_err + $pyjs_msg);
            $pyjs.debug_msg = $pyjs_msg;
            debugger;
        }
    }
    switch (%(dbg)s_retry) {
        case 1:
            %(dbg)s_res=%(call_code)s;
            break;
        case 2:
            break;
        default:
            throw %(dbg)s_err;
    }
}return %(dbg)s_res})()""" % locals()
        return call_code

    __generator_code_str = """\
var $generator_state = [0], $generator_exc = [null], $yield_value = null, $exc = null, $is_executing=false;
var $generator = function () {};
$generator['next'] = function (noStop) {
%(src1)s
    var $res;
    $yield_value = $exc = null;
    try {
        $res = $generator['$genfunc']();
        $is_executing=false;
        if (typeof $res == 'undefined') {
            if (noStop === true) {
                $generator_state[0] = -1;
                return;
            }
            throw pyjslib.StopIteration;
        }
    } catch (e) {
%(src2)s
        $is_executing=false;
        $generator_state[0] = -1;
        if (noStop === true && e === pyjslib['StopIteration']) {
            return;
        }
        throw e;
    }
    return $res;
};
$generator['__iter__'] = function () {return $generator;};
$generator['send'] = function ($val) {
%(src1)s
    $yield_value = $val;
    $exc = null;
    try {
        var $res = $generator['$genfunc']();
        if (typeof $res == 'undefined') throw pyjslib.StopIteration;
    } catch (e) {
%(src2)s
        $generator_state[0] = -1;
        $is_executing=false;
        throw e;
    }
    $is_executing=false;
    return $res;
};
$generator['$$throw'] = function ($exc_type, $exc_value) {
%(src1)s
    $yield_value = null;
    $exc=(typeof $exc_value == 'undefined'?$exc_type():$exc_type($exc_value));
    try {
        var $res = $generator['$genfunc']();
    } catch (e) {
%(src2)s
        $generator_state[0] = -1;
        $is_executing=false;
        throw (e);
    }
    $is_executing=false;
    return $res;
};
$generator['close'] = function () {
%(src1)s
    $yield_value = null;
    $exc=pyjslib['GeneratorExit'];
    try {
        var $res = $generator['$genfunc']();
        $is_executing=false;
        if (typeof $res != 'undefined') throw pyjslib.RuntimeError('generator ignored GeneratorExit');
    } catch (e) {
%(src2)s
        $generator_state[0] = -1;
        $is_executing=false;
        if (e.__name__ == 'StopIteration' || e.__name__ == 'GeneratorExit') return null;
        throw (e);
    }
    return null;
};
$generator['$genfunc'] = function () {
    var $yielding = false;
    if ($is_executing) throw pyjslib.ValueError('generator already executing');
    $is_executing = true;
"""
    __generator_code_str = __generator_code_str.replace("    ", "\t").replace("\n", "\n%(s)s")

    def generator(self, code):
        if self.is_generator:
            s = self.spacing()
            if self.source_tracking:
                src1 = "var $pyjs__trackstack_size_%d = $pyjs.trackstack.length;" % self.stacksize_depth
                src2 = """\
%(s)ssys.save_exception_stack();
%(s)sif ($pyjs.trackstack.length > $pyjs__trackstack_size_%(d)d) {
%(s)s\t$pyjs.trackstack = $pyjs.trackstack.slice(0,$pyjs__trackstack_size_%(d)d);
%(s)s\t$pyjs.track = $pyjs.trackstack.slice(-1)[0];
%(s)s}
%(s)s$pyjs.track.module='%(m)s';""" % {'s': self.spacing(), 'd': self.stacksize_depth, 'm': self.module_name}
            else:
                src1 = src2 = ""

            print >>self.output, self.__generator_code_str % locals()
            self.indent()
            print >>self.output, code
            print >>self.output, self.spacing(), "return;"
            print >>self.output, self.dedent(), "};"
            print >>self.output, self.spacing(), "return $generator;"
        else:
            print >>self.output, captured_output,

    def generator_switch_open(self):
        if self.is_generator:
            self.indent()

    def generator_switch_case(self, increment):
        if self.is_generator:
            if increment:
                self.generator_states[-1] += 1
            n_states = len(self.generator_states)
            state = self.generator_states[-1]
            if self.generator_states[-1] == 0:
                self.dedent()
                print >>self.output, self.indent() + """if (typeof $generator_state[%d] == 'undefined' || $generator_state[%d] === 0) {""" % (n_states-1, n_states-1)
                self.generator_clear_state()
                if n_states == 1:
                    self.generator_throw()
            else:
                if increment:
                    print >>self.output, self.spacing() + """$generator_state[%d]=%d;""" % (n_states-1, state)
                print >>self.output, self.dedent() + "}"
                print >>self.output, self.indent() + """if ($generator_state[%d] == %d) {""" % (n_states-1, state)

    def generator_switch_close(self):
        if self.is_generator:
            print >>self.output, self.dedent() + "}"

    def generator_add_state(self):
        if self.is_generator:
            self.generator_states.append(0)
            self.state_max_depth = len(self.generator_states)

    def generator_del_state(self):
        if self.is_generator:
            del self.generator_states[-1]

    def generator_clear_state(self):
        if self.is_generator:
            n_states = len(self.generator_states)
            print >>self.output, self.spacing() + """for (var $i = %d ; $i < ($generator_state.length<%d?%d:$generator_state.length); $i++) $generator_state[$i]=0;""" % (n_states-1, n_states+1, n_states+1)

    def generator_reset_state(self):
        if self.is_generator:
            n_states = len(self.generator_states)
            print >>self.output, self.spacing() + """$generator_state.splice(%d, $generator_state.length-%d);""" % (n_states, n_states)

    def generator_throw(self):
        print >>self.output, self.indent() + "if (typeof $exc != 'undefined' && $exc !== null) {"
        print >>self.output, self.spacing() + "$yielding = null;"
        print >>self.output, self.spacing() + "$generator_state[%d] = -1;" % (len(self.generator_states)-1,)
        print >>self.output, self.spacing() + "throw $exc;"
        print >>self.output, self.dedent() + "}"


    def func_args(self, node, current_klass, function_name, bind_type, args, stararg, dstararg):
        try:
            bind_type = BIND_TYPES_NUMERIC[bind_type]
        except KeyError:
            raise TranslationError("Unknown bind type: %s" % bind_type, node)
        _args = []
        default_pos = len(args) - len(node.defaults)
        for idx, arg in enumerate(args):
            if idx < default_pos:
                _args.append("['%s']" % arg)
            else:
                default_value = self.expr(node.defaults[idx-default_pos], current_klass)
                _args.append("""['%s', %s]""" % (arg, default_value))
        args = ",".join(_args)
        if dstararg:
            args = "['%s'],%s" % (dstararg, args)
        else:
            args = "null,%s" % args
        if stararg:
            args = "'%s',%s" % (stararg, args)
        else:
            args = "null,%s" % args
        args = '[' + args + ']'
        # remove any empty tail
        if args.endswith(',]'):
            args = args[:-2] + ']'
        if function_name is None:
            print >>self.output, "\t, %d, %s);" % (bind_type, args)
        else:
            print >>self.output, self.spacing() + "%s.__bind_type__ = %s;" % (function_name, bind_type)
            print >>self.output, self.spacing() + "%s.__args__ = %s;" % (function_name, args)

    def _instance_method_init(self, node, arg_names, varargname, kwargname,
                              current_klass, output=None):
        output = output or self.output
        maxargs1 = len(arg_names) - 1
        maxargs2 = len(arg_names)
        minargs1 = maxargs1 - len(node.defaults)
        minargs2 = maxargs2 - len(node.defaults)
        if node.kwargs:
            maxargs1 += 1
            maxargs2 += 1
        maxargs1str = "%d" % maxargs1
        maxargs2str = "%d" % maxargs2
        if node.varargs:
            argcount1 = "arguments.length < %d" % minargs1
            maxargs1str = "null"
        elif minargs1 == maxargs1:
            argcount1 = "arguments.length != %d" % minargs1
        else:
            argcount1 = "(arguments.length < %d || arguments.length > %d)" % (minargs1, maxargs1)
        if node.varargs:
            argcount2 = "arguments.length < %d" % minargs2
            maxargs2str = "null"
        elif minargs2 == maxargs2:
            argcount2 = "arguments.length != %d" % minargs2
        else:
            argcount2 = "(arguments.length < %d || arguments.length > %d)" % (minargs2, maxargs2)

        print >> output, self.indent() + """\
if (this.__is_instance__ === true) {\
"""
        if arg_names:
            print >> output, self.spacing() + """\
var %s = this;\
""" % arg_names[0]

        if node.varargs:
            self._varargs_handler(node, varargname, maxargs1)

        if node.kwargs:
            print >> output, self.spacing() + """\
var %s = arguments.length >= %d ? arguments[arguments.length-1] : arguments[arguments.length];\
""" % (kwargname, maxargs1)
            s = self.spacing()
            print >> output, """\
%(s)sif (typeof %(kwargname)s != 'object' || %(kwargname)s.__name__ != 'dict' || typeof %(kwargname)s.$pyjs_is_kwarg == 'undefined') {\
""" % locals()
            if node.varargs:
                print >> output, """\
%(s)s\tif (typeof %(kwargname)s != 'undefined') %(varargname)s.__array.push(%(kwargname)s);\
""" % locals()
            print >> output, """\
%(s)s\t%(kwargname)s = arguments[arguments.length+1];
%(s)s} else {
%(s)s\tdelete %(kwargname)s['$pyjs_is_kwarg'];
%(s)s}\
""" % locals()

        if self.function_argument_checking:
            print >> output, self.spacing() + """\
if ($pyjs.options.arg_count && %s) $pyjs__exception_func_param(arguments.callee.__name__, %d, %s, arguments.length+1);\
""" % (argcount1, minargs2, maxargs2str)

        print >> output, self.dedent() + """\
} else {\
"""
        self.indent()

        if arg_names:
            print >> output, self.spacing() + """\
var %s = arguments[0];\
""" % arg_names[0]
        arg_idx = 0
        for arg_name in arg_names[1:]:
            arg_idx += 1
            print >> output, self.spacing() + """\
%s = arguments[%d];\
""" % (arg_name, arg_idx)

        if node.varargs:
            self._varargs_handler(node, varargname, maxargs2)

        if node.kwargs:
            print >> output, self.spacing() + """\
var %s = arguments.length >= %d ? arguments[arguments.length-1] : arguments[arguments.length];\
""" % (kwargname, maxargs2)
            s = self.spacing()
            print >> output, """\
%(s)sif (typeof %(kwargname)s != 'object' || %(kwargname)s.__name__ != 'dict' || typeof %(kwargname)s.$pyjs_is_kwarg == 'undefined') {\
""" % locals()
            if node.varargs:
                print >> output, """\
%(s)s\tif (typeof %(kwargname)s != 'undefined') %(varargname)s.__array.push(%(kwargname)s);\
""" % locals()
            print >> output, """\
%(s)s\t%(kwargname)s = arguments[arguments.length+1];
%(s)s} else {
%(s)s\tdelete %(kwargname)s['$pyjs_is_kwarg'];
%(s)s}\
""" % locals()

        if self.function_argument_checking:
            print >> output, """\
%sif ($pyjs.options.arg_is_instance && self.__is_instance__ !== true) $pyjs__exception_func_instance_expected(arguments.callee.__name__, arguments.callee.__class__.__name__, self);
%sif ($pyjs.options.arg_count && %s) $pyjs__exception_func_param(arguments.callee.__name__, %d, %s, arguments.length);\
""" % (self.spacing(), self.spacing(), argcount2, minargs2, maxargs2str)

        print >> output, self.dedent() + "}"

        if arg_names and self.function_argument_checking:
            print >> output, """\
%(s)sif ($pyjs.options.arg_instance_type) {
%(s)s\tif (%(self)s.prototype.__md5__ !== '%(__md5__)s') {
%(s)s\t\tif (!pyjslib['_isinstance'](%(self)s, arguments['callee']['__class__'])) {
%(s)s\t\t\t$pyjs__exception_func_instance_expected(arguments['callee']['__name__'], arguments['callee']['__class__']['__name__'], %(self)s);
%(s)s\t\t}
%(s)s\t}
%(s)s}\
""" % {'s': self.spacing(), 'self': arg_names[0], '__md5__': current_klass.__md5__}

    def _static_method_init(self, node, arg_names, varargname, kwargname,
                            current_klass, output=None):
        output = output or self.output
        maxargs = len(arg_names)
        minargs = maxargs - len(node.defaults)
        maxargsstr = "%d" % maxargs
        if node.kwargs:
            maxargs += 1
        if node.varargs:
            argcount = "arguments.length < %d" % minargs
            maxargsstr = "null"
        elif minargs == maxargs:
            argcount = "arguments.length != %d" % minargs
        else:
            argcount = "(arguments.length < %d || arguments.length > %d)" % (minargs, maxargs)
        if self.function_argument_checking:
            print >> output, self.spacing() + """\
if ($pyjs.options.arg_count && %s) $pyjs__exception_func_param(arguments.callee.__name__, %d, %s, arguments.length);\
""" % (argcount, minargs, maxargsstr)

        if node.varargs:
            self._varargs_handler(node, varargname, maxargs)

        if node.kwargs:
            print >> output, self.spacing() + """\
var %s = arguments.length >= %d ? arguments[arguments.length-1] : arguments[arguments.length];\
""" % (kwargname, maxargs)
            s = self.spacing()
            print >> output, """\
%(s)sif (typeof %(kwargname)s != 'object' || %(kwargname)s.__name__ != 'dict' || typeof %(kwargname)s.$pyjs_is_kwarg == 'undefined') {\
""" % locals()
            if node.varargs:
                print >> output, """\
%(s)s\tif (typeof %(kwargname)s != 'undefined') %(varargname)s.__array.push(%(kwargname)s);\
""" % locals()
            print >> output, """\
%(s)s\t%(kwargname)s = arguments[arguments.length+1];
%(s)s} else {
%(s)s\tdelete %(kwargname)s['$pyjs_is_kwarg'];
%(s)s}\
""" % locals()


    def _class_method_init(self, node, arg_names, varargname, kwargname,
                           current_klass, output=None):
        output = output or self.output
        maxargs = max(0, len(arg_names) -1)
        minargs = max(0, maxargs - len(node.defaults))
        maxargsstr = "%d" % (maxargs+1)
        if node.kwargs:
            maxargs += 1
        if node.varargs:
            argcount = "arguments.length < %d" % minargs
            maxargsstr = "null"
        elif minargs == maxargs:
            argcount = "arguments.length != %d" % minargs
            maxargsstr = "%d" % (maxargs)
        else:
            argcount = "(arguments.length < %d || arguments.length > %d)" % (minargs, maxargs)
        if self.function_argument_checking:
            print >> output, """\
    if ($pyjs.options.arg_is_instance && this.__is_instance__ !== true && this.__is_instance__ !== false) $pyjs__exception_func_class_expected(arguments.callee.__name__, arguments.callee.__class__.__name__);
    if ($pyjs.options.arg_count && %s) $pyjs__exception_func_param(arguments.callee.__name__, %d, %s, arguments.length);\
""" % (argcount, minargs+1, maxargsstr)

        print >> output, """\
    var %s = this.prototype;\
""" % (arg_names[0],)

        if node.varargs:
            self._varargs_handler(node, varargname, maxargs)

        if node.kwargs:
            print >> output, self.spacing() + """\
var %s = arguments.length >= %d ? arguments[arguments.length-1] : arguments[arguments.length];\
""" % (kwargname, maxargs)
            s = self.spacing()
            print >> output, """\
%(s)sif (typeof %(kwargname)s != 'object' || %(kwargname)s.__name__ != 'dict' || typeof %(kwargname)s.$pyjs_is_kwarg == 'undefined') {\
""" % locals()
            if node.varargs:
                print >> output, """\
%(s)s\tif (typeof %(kwargname)s != 'undefined') %(varargname)s.__array.push(%(kwargname)s);\
""" % locals()
            print >> output, """\
%(s)s\t%(kwargname)s = arguments[arguments.length+1];
%(s)s}\
""" % locals()

    def _default_args_handler(self, node, arg_names, current_klass, kwargname,
                              output=None):
        output = output or self.output
        if node.kwargs:
            # This is necessary when **kwargs in function definition
            # and the call didn't pass the pyjs_kwargs_call().
            # See libtest testKwArgsInherit
            # This is not completely safe: if the last element in arguments 
            # is an dict and the corresponding argument shoud be a dict and 
            # the kwargs should be empty, the kwargs gets incorrectly the 
            # dict and the argument becomes undefined.
            # E.g.
            # def fn(a = {}, **kwargs): pass
            # fn({'a':1}) -> a gets undefined and kwargs gets {'a':1}
            revargs = arg_names[0:]
            revargs.reverse()
            print >> output, """\
%(s)sif (typeof %(k)s == 'undefined') {
%(s)s\t%(k)s = pyjslib['__empty_dict']();\
""" % {'s': self.spacing(), 'k': kwargname}
            for v in revargs:
                print >> output, """\
%(s)s\tif (typeof %(v)s != 'undefined') {
%(s)s\t\tif (%(v)s !== null && typeof %(v)s['$pyjs_is_kwarg'] != 'undefined') {
%(s)s\t\t\t%(k)s = %(v)s;
%(s)s\t\t\t%(v)s = arguments[%(a)d];
%(s)s\t\t}
%(s)s\t} else\
""" % {'s': self.spacing(), 'v': v, 'k': kwargname, 'a': len(arg_names)},
            print >> output, """\
{
%(s)s\t}
%(s)s}\
""" % {'s': self.spacing()}

        if len(node.defaults):
            default_pos = len(arg_names) - len(node.defaults)
            for default_node in node.defaults:
                default_value = self.expr(default_node, current_klass)
                default_name = arg_names[default_pos]
                default_pos += 1
                #print >> output, self.spacing() + "if (typeof %s == 'undefined') %s=%s;" % (default_name, default_name, default_value)
                print >> output, self.spacing() + "if (typeof %s == 'undefined') %s=arguments.callee.__args__[%d][1];" % (default_name, default_name, default_pos+1)

    def _varargs_handler(self, node, varargname, start):
        if node.kwargs:
            end = "arguments.length-1"
            start -= 1
        else:
            end = "arguments.length"
        print >> self.output, """\
%(s)svar %(v)s = pyjslib['tuple']($pyjs_array_slice.call(arguments,%(b)d,%(e)s));
""" % {'s': self.spacing(), 'v': varargname, 'b': start, 'e': end}

    def _kwargs_parser(self, node, function_name, arg_names, current_klass, method_ = False):
        default_pos = len(arg_names) - len(node.defaults)
        if not method_:
            print >>self.output, self.indent() + function_name+'.parse_kwargs = function (', ", ".join(["__kwargs"]+arg_names), ") {"
        else:
            print >>self.output, self.indent() + ", function (", ", ".join(["__kwargs"]+arg_names), ") {"
        print >>self.output, self.spacing() + "var __r = [];"
        print >>self.output, self.spacing() + "var $pyjs__va_arg_start = %d;" % (len(arg_names)+1)

        if len(arg_names) > 0:
            print >>self.output, """\
%(s)sif (typeof %(arg_name)s != 'undefined' && this.__is_instance__ === false && %(arg_name)s.__is_instance__ === true) {
%(s)s\t__r.push(%(arg_name)s);
%(s)s\t$pyjs__va_arg_start++;""" % {'s': self.spacing(), 'arg_name': arg_names[0]}
            idx = 1
            for arg_name in arg_names:
                idx += 1
                print >>self.output, """\
%(s)s\t%(arg_name)s = arguments[%(idx)d];\
""" % {'s': self.spacing(), 'arg_name': arg_name, 'idx': idx}
            print >>self.output, self.spacing() + "}"

        for arg_name in arg_names:
            if self.function_argument_checking:
                print >>self.output, """\
%(s)sif (typeof %(arg_name)s == 'undefined') {
%(s)s\t%(arg_name)s=__kwargs.%(arg_name)s;
%(s)s\tdelete __kwargs.%(arg_name)s;
%(s)s} else if ($pyjs.options.arg_kwarg_multiple_values && typeof __kwargs.%(arg_name)s != 'undefined') {
%(s)s\t$pyjs__exception_func_multiple_values('%(function_name)s', '%(arg_name)s');
%(s)s}\
""" % {'s': self.spacing(), 'arg_name': arg_name, 'function_name': function_name}
            else:
                print >>self.output, self.indent() + "if (typeof %s == 'undefined') {"%(arg_name)
                print >>self.output, self.spacing() + "%s=__kwargs.%s;"% (arg_name, arg_name)
                print >>self.output, self.dedent() + "}"
            print >>self.output, self.spacing() + "__r.push(%s);" % arg_name

        if self.function_argument_checking and not node.kwargs:
            print >>self.output, """\
%(s)sif ($pyjs.options.arg_kwarg_unexpected_keyword) {
%(s)s\tfor (var i in __kwargs) {
%(s)s\t\t$pyjs__exception_func_unexpected_keyword('%(function_name)s', i);
%(s)s\t}
%(s)s}\
""" % {'s': self.spacing(), 'function_name': function_name}

        # Always add all remaining arguments. Needed for argument checking _and_ if self != this;
        print >>self.output, """\
%(s)sfor (var $pyjs__va_arg = $pyjs__va_arg_start;$pyjs__va_arg < arguments.length;$pyjs__va_arg++) {
%(s)s\t__r.push(arguments[$pyjs__va_arg]);
%(s)s}
""" % {'s': self.spacing()}
        if node.kwargs:
            print >>self.output, self.spacing() + "__r.push(pyjslib['dict'](__kwargs));"
        print >>self.output, self.spacing() + "return __r;"
        if not method_:
            print >>self.output, self.dedent() + "};"
        else:
            print >>self.output, self.dedent() + "});"


    def _import(self, node, current_klass, root_level = False):
        # XXX: hack for in-function checking, we should have another
        # object to check our scope
        self._doImport(node.names, current_klass, root_level, True)

    def _doImport(self, names, current_klass, root_level, assignBase, absPath=False):
        if root_level:
            modtype = 'root-module'
        else:
            modtype = 'module'
        for importName, importAs in names:
            if importName == '__pyjamas__':
                continue
            if importName.endswith(".js"):
                self.add_imported_module(importName)
                continue
            # "searchList" contains a list of possible module names :
            #   We create the list at compile time to save runtime.
            searchList = []
            context = self.module_name
            if '.' in context:
                # our context lives in a package so it is possible to have a
                # relative import
                package = context.rsplit('.', 1)[0]
                relName = package + '.' + importName
                searchList.append(relName)
                if '.' in importName:
                    searchList.append(relName.rsplit('.', 1)[0])
            # the absolute path
            searchList.append(importName)
            if '.' in importName:
                searchList.append(importName.rsplit('.', 1)[0])

            mod = self.lookup(importName)
            package_mod = self.lookup(importName.split('.', 1)[0])

            import_stmt = None
            if (   mod[0] != 'root-module'
                or (assignBase and not package_mod[0] in ['root-module', 'module'])
               ):
                # the import statement
                if absPath:
                    context = 'null'
                else:
                    context = self.import_context
                import_stmt = "pyjslib['___import___']('%s', %s" % (
                                    importName,
                                    context,
                                    )
                if not assignBase:
                    print >> self.output, self.spacing() + import_stmt + 'null, false);'
                self._lhsFromName(importName, current_klass, modtype)
                self.add_imported_module(importName)
            if assignBase:
                # get the name in scope
                package_name = importName.split('.')[0]
                if importAs:
                    ass_name = importAs
                    if not import_stmt is None:
                        import_stmt += ', null, false'
                else:
                    ass_name = package_name
                lhs = self._lhsFromName(ass_name, current_klass, modtype)
                if importAs:
                    mod_name = importName
                else:
                    mod_name = ass_name
                if import_stmt is None:
                    #stmt = "%s = $pyjs.__modules__['%s'];"% (lhs, "']['".join(mod_name.split('.')))
                    parent_mod_name = mod_name.split('.')
                    if len(parent_mod_name) == 1:
                        stmt = "%s = $pyjs.loaded_modules['%s'];"% (lhs, mod_name)
                    else:
                        mod_name = parent_mod_name[-1]
                        parent_mod_name = '.'.join(parent_mod_name[:-1])
                        stmt = "%s = $pyjs.loaded_modules['%s']['%s'];"% (lhs, parent_mod_name, mod_name)
                else:
                    stmt = "%s = %s);"% (lhs, import_stmt)
                print >> self.output, self.spacing() + stmt

    def _from(self, node, current_klass, root_level = False):
        if node.modname == '__pyjamas__':
            # special module to help make pyjamas modules loadable in
            # the python interpreter
            for name in node.names:
                ass_name = name[1] or name[0]
                try:
                    jsname =  getattr(__pyjamas__, name[0])
                    if callable(jsname):
                        self.add_lookup("__pyjamas__", ass_name, name[0])
                    else:
                        self.add_lookup("__pyjamas__", ass_name, jsname)
                except AttributeError, e:
                    #raise TranslationError("Unknown __pyjamas__ import: %s" % name, node)
                    pass
            return
        if node.modname == '__javascript__':
            for name in node.names:
                ass_name = name[1] or name[0]
                self.add_lookup("__javascript__", ass_name, ass_name)
            return
        # XXX: hack for in-function checking, we should have another
        # object to check our scope
        absPath = False
        modname = node.modname
        if hasattr(node, 'level') and node.level > 0:
            absPath = True
            modname = self.module_name.split('.')
            level = node.level
            if len(modname) < level:
                raise TranslationError(
                    "Attempted relative import beyond toplevel package",
                    node, self.module_name)
            if node.modname != '':
                level += 1
            if level > 1:
                modname = '.'.join(modname[:-(node.level-1)])
            else:
                modname = self.module_name
            if node.modname != '':
                modname += '.' + node.modname
                if modname[0] == '.':
                    modname = modname[1:]
        for name in node.names:
            sub = modname + '.' + name[0]
            ass_name = name[1] or name[0]
            self._doImport(((sub, ass_name),), current_klass, root_level, True, absPath)

    def _function(self, node, current_klass, force_local=False):
        if self.is_class_definition:
            return self._method(node, current_klass)
        save_top_level = self.top_level
        self.push_options()
        save_has_js_return = self.has_js_return
        self.has_js_return = False
        save_has_yield = self.has_yield
        self.has_yield = False
        save_is_generator = self.is_generator
        self.is_generator = False
        save_generator_states = self.generator_states
        self.generator_states = [0]
        self.state_max_depth = len(self.generator_states)

        if not save_top_level or force_local:
            function_name = node.name
        else:
            function_name = self.modpfx() + node.name
        function_name = self.add_lookup('function', node.name, function_name)
        staticmethod, classmethod, decorator_code = self.parse_decorators(node, node.name, current_klass)
        if staticmethod or classmethod:
            raise TranslationError(
                "Decorators staticmethod and classmethod not implemented for functions",
                v.node, self.module_name)
        self.push_lookup()

        arg_names = []
        for arg in node.argnames:
            if isinstance(arg, tuple):
                for a in arg:
                    arg_names.append(self.add_lookup('variable', a, a))
            else:
                arg_names.append(self.add_lookup('variable', arg, arg))
        normal_arg_names = list(arg_names)
        if node.kwargs:
            kwargname = normal_arg_names.pop()
        else:
            kwargname = None
        if node.varargs:
            varargname = normal_arg_names.pop()
        else:
            varargname = None
        declared_arg_names = list(normal_arg_names)
        #if node.kwargs: declared_arg_names.append(kwargname)

        function_args = "(" + ", ".join(declared_arg_names) + ")"
        print >>self.output, self.indent() + "%s = function%s {" % (function_name, function_args)
        self._static_method_init(node, declared_arg_names, varargname, kwargname, None)
        self._default_args_handler(node, declared_arg_names, None, kwargname)

        local_arg_names = normal_arg_names + declared_arg_names

        if node.kwargs:
            local_arg_names.append(kwargname)
        if node.varargs:
            local_arg_names.append(varargname)

        self.top_level = False
        save_output = self.output
        self.output = StringIO()
        if self.source_tracking:
            print >>self.output, self.spacing() + "$pyjs.track={module:'%s',lineno:%d};$pyjs.trackstack.push($pyjs.track);" % (self.module_name, node.lineno)
        self.track_lineno(node, True)
        for child in node.code:
            self._stmt(child, None)
        if not self.has_yield and self.source_tracking and self.has_js_return:
            self.source_tracking = False
            self.output = StringIO()
            for child in node.code:
                self._stmt(child, None)
        elif self.has_yield:
            if self.has_js_return:
                self.source_tracking = False
            self.is_generator = True
            self.generator_states = [0]
            self.output = StringIO()
            self.indent()
            if self.source_tracking:
                print >>self.output, self.spacing() + "$pyjs.track={module:'%s',lineno:%d};$pyjs.trackstack.push($pyjs.track);" % (self.module_name, node.lineno)
            self.track_lineno(node, True)
            self.generator_switch_open()
            self.generator_switch_case(increment=False)
            for child in node.code:
                self._stmt(child, None)
            self.generator_switch_case(increment=True)
            self.generator_switch_close()
            self.dedent()

        captured_output = self.output.getvalue()
        self.output = save_output
        print >>self.output, self.local_js_vars_decl(local_arg_names)
        if self.is_generator:
            self.generator(captured_output)
        else:
            print >>self.output, captured_output,

            # we need to return null always, so it is not undefined
            if node.code.nodes:
                lastStmt = node.code.nodes[-1]
            else:
                lastStmt = None
            if not isinstance(lastStmt, self.ast.Return):
                if self.source_tracking:
                    print >>self.output, self.spacing() + "$pyjs.trackstack.pop();$pyjs.track=$pyjs.trackstack.pop();$pyjs.trackstack.push($pyjs.track);"
                # FIXME: check why not on on self._isNativeFunc(lastStmt)
                if not self._isNativeFunc(lastStmt):
                    print >>self.output, self.spacing() + "return null;"

        print >>self.output, self.dedent() + "};"
        print >>self.output, self.spacing() + "%s.__name__ = '%s';\n" % (function_name, node.name)

        self.pop_lookup()
        self.func_args(node, current_klass, function_name, 'static', declared_arg_names, varargname, kwargname)

        if decorator_code:
            decorator_code = decorator_code % function_name
            if function_name != decorator_code:
                print >>self.output, self.spacing() + "%s = %s;" % (function_name, decorator_code)

        self.generator_states = save_generator_states
        self.state_max_depth = len(self.generator_states)
        self.is_generator = save_is_generator
        self.has_yield = save_has_yield
        self.has_js_return = save_has_js_return
        self.pop_options()
        self.top_level = save_top_level

    def _assert(self, node, current_klass):
        expr = self.expr(node.test, current_klass)
        if node.fail:
            fail = self.expr(node.fail, current_klass)
        else:
            fail = ''
        print >>self.output, self.spacing() + "if (!( " + expr + " )) {"
        print >>self.output, self.spacing() + "   throw pyjslib['AssertionError'](%s);" % fail
        print >>self.output, self.spacing() + " }"

    def _return(self, node, current_klass):
        expr = self.expr(node.value, current_klass)
        # in python a function call always returns None, so we do it
        # here too
        self.track_lineno(node)
        if self.is_generator:
            if isinstance(node.value, self.ast.Const):
                if node.value.value is None:
                    if self.source_tracking:
                        print >>self.output, self.spacing() + "$pyjs.trackstack.pop();$pyjs.track=$pyjs.trackstack.pop();$pyjs.trackstack.push($pyjs.track);"
                    print >>self.output, self.spacing() + "return;"
                    return
            raise TranslationError(
                "'return' with argument inside generator",
                 node, self.module_name)
        elif self.source_tracking:
            print >>self.output, self.spacing() + "var $pyjs__ret = " + expr + ";"
            print >>self.output, self.spacing() + "$pyjs.trackstack.pop();$pyjs.track=$pyjs.trackstack.pop();$pyjs.trackstack.push($pyjs.track);"
            print >>self.output, self.spacing() + "return $pyjs__ret;"
        else:
            print >>self.output, self.spacing() + "return " + expr + ";"


    def _yield(self, node, current_klass):
        # http://www.python.org/doc/2.5.2/ref/yieldexpr.html
        self.has_yield = True
        expr = self.expr(node.value, current_klass)
        self.track_lineno(node)
        #print >>self.output, self.spacing() + "$generator_state[%d] = %d;" % (len(self.generator_states)-1, self.generator_states[-1]+1)

        print >>self.output, self.spacing() + "$yield_value = " + expr + ";"
        if self.source_tracking:
            print >>self.output, self.spacing() + "$pyjs.trackstack.pop();$pyjs.track=$pyjs.trackstack.pop();$pyjs.trackstack.push($pyjs.track);"
        print >>self.output, self.spacing() + "$yielding = true;"
        print >>self.output, self.spacing() + "$generator_state[%d] = %d;" % (len(self.generator_states)-1, self.generator_states[-1]+1)
        print >>self.output, self.spacing() + "return $yield_value;"
        self.generator_switch_case(increment=True)
        self.generator_throw()

    def _yield_expr(self, node, current_klass):
        self._yield(node, current_klass)
        return '$yield_value'


    def _break(self, node, current_klass):
        self.generator_switch_case(increment=True)
        print >>self.output, self.spacing() + "break;"


    def _continue(self, node, current_klass):
        print >>self.output, self.spacing() + "continue;"


    def _callfunc_code(self, v, current_klass):

        self.ignore_debug = False
        method_name = None
        if isinstance(v.node, self.ast.Name):
            name_type, pyname, jsname, depth, is_local = self.lookup(v.node.name)
            if name_type == '__pyjamas__':
                try:
                    raw_js = getattr(__pyjamas__, v.node.name)
                    if callable(raw_js):
                        raw_js, has_js_return = raw_js(self, v)
                        if has_js_return:
                            self.has_js_return = True
                    return raw_js
                except AttributeError, e:
                    raise TranslationError(
                        "Unknown __pyjamas__ function %s" % pyname,
                         v.node, self.module_name)
                except TranslationError, e:
                    raise TranslationError(e.msg, v, self.module_name)
            elif v.node.name == 'locals':
                return """pyjslib.dict({%s})""" % (",".join(["'%s': %s" % (pyname, self.lookup_stack[-1][pyname][2]) for pyname in self.lookup_stack[-1] if self.lookup_stack[-1][pyname][0] not in ['__pyjamas__', 'global']]))
            elif v.node.name == 'len' and depth == -1 and len(v.args) == 1:
                expr = self.expr(v.args[0], current_klass)
                return self.inline_len_code(expr)
            else:
                if name_type is None:
                    # What to do with a (yet) unknown name?
                    # Just nothing...
                    call_name = self.scopeName(v.node.name, depth, is_local)
                else:
                    call_name = jsname
            call_args = []
        elif isinstance(v.node, self.ast.Getattr):
            attrname = self.attrib_remap(v.node.attrname)
            if isinstance(v.node.expr, self.ast.Name):
                call_name, method_name = self._name2(v.node.expr, current_klass, attrname)
                call_args = []
            elif isinstance(v.node.expr, self.ast.Getattr):
                call_name = self._getattr2(v.node.expr, current_klass, v.node.attrname)
                method_name = call_name.pop()
                call_name = self.attrib_join(call_name)
                call_args = []
            elif isinstance(v.node.expr, self.ast.CallFunc):
                call_name = self._callfunc(v.node.expr, current_klass)
                method_name = attrname
                call_args = []
            elif isinstance(v.node.expr, self.ast.Subscript):
                call_name = self._subscript(v.node.expr, current_klass)
                method_name = attrname
                call_args = []
            elif isinstance(v.node.expr, self.ast.Const):
                call_name = self.expr(v.node.expr, current_klass)
                method_name = attrname
                call_args = []
            elif isinstance(v.node.expr, self.ast.Slice):
                call_name = self._slice(v.node.expr, current_klass)
                method_name = attrname
                call_args = []
            else:
                raise TranslationError(
                    "unsupported type (in _callfunc)", v.node.expr, self.module_name)
        elif isinstance(v.node, self.ast.CallFunc):
            call_name = self._callfunc(v.node, current_klass)
            call_args = []
        elif isinstance(v.node, self.ast.Subscript):
            call_name = self._subscript(v.node, current_klass)
            call_args = []
        else:
            raise TranslationError(
                "unsupported type (in _callfunc)", v.node, self.module_name)

        if method_name in pyjs_attrib_remap:
            method_name = pyjs_attrib_remap[method_name]

        call_name = strip_py(call_name)

        kwargs = []
        star_arg_name = None
        if v.star_args: 
            star_arg_name = self.expr(v.star_args, current_klass)
        dstar_arg_name = None
        if v.dstar_args:
            dstar_arg_name = self.expr(v.dstar_args, current_klass)

        for ch4 in v.args:
            if isinstance(ch4, self.ast.Keyword):
                kwarg = self.vars_remap(ch4.name) + ":" + \
                        self.expr(ch4.expr, current_klass)
                kwargs.append(kwarg)
            else:
                arg = self.expr(ch4, current_klass)
                call_args.append(arg)

        if kwargs:
            fn_args = ", ".join(['{' + ', '.join(kwargs) + '}']+call_args)
        else:
            fn_args = ", ".join(['{}']+call_args)

        if kwargs or star_arg_name or dstar_arg_name:
            if not star_arg_name:
                star_arg_name = 'null'
            if not dstar_arg_name:
                dstar_arg_name = 'null'
            if method_name is None:
                call_code = ("$pyjs_kwargs_call(null, "+call_name+", "
                                  + star_arg_name 
                                  + ", " + dstar_arg_name
                                  + ", ["+fn_args+"]"
                                  + ")")
            else:
                call_code = ("$pyjs_kwargs_call("+call_name+", '"+method_name+"', "
                                  + star_arg_name 
                                  + ", " + dstar_arg_name
                                  + ", ["+fn_args+"]"
                                  + ")")
        else:
            if not method_name is None:
                call_name = "%s['%s']" % (call_name, method_name)
            call_code = call_name + "(" + ", ".join(call_args) + ")"
        return call_code

    def _callfunc(self, v, current_klass):
        call_code = self._callfunc_code(v, current_klass)
        if not self.ignore_debug:
            call_code = self.track_call(call_code, v.lineno)
        return call_code

    def _print(self, node, current_klass):
        if not self.print_statements:
            return
        call_args = []
        for ch4 in node.nodes:
            arg = self.expr(ch4, current_klass)
            call_args.append(arg)
        print >>self.output, self.spacing() + self.track_call("pyjslib['printFunc']([%s], %d)" % (', '.join(call_args), int(isinstance(node, self.ast.Printnl))), node.lineno) + ';'

    def _tryFinally(self, node, current_klass):
        body = node.body
        if not isinstance(node.body, self.ast.TryExcept):
            body = node
        try: # python2.N
            node.body.final = node.final
        except: # lib2to3
            node.body.final_ = node.final_
        self._tryExcept(body, current_klass)

    def _tryExcept(self, node, current_klass):
        save_is_generator = self.is_generator
        if self.is_generator:
            self.is_generator = self.compiler.walk(node, GeneratorExitVisitor(), walker=GeneratorExitVisitor()).has_yield
        self.try_depth += 1
        self.stacksize_depth += 1
        save_state_max_depth = self.state_max_depth
        start_states = len(self.generator_states)
        pyjs_try_err = '$pyjs_try_err'
        if self.source_tracking:
            print >>self.output, self.spacing() + "var $pyjs__trackstack_size_%d = $pyjs.trackstack.length;" % self.stacksize_depth
        self.generator_switch_case(increment=True)
        print >>self.output, self.indent() + "try {"
        if self.is_generator:
            print >> self.output, self.spacing() + "if (typeof $generator_exc[%d] != 'undefined' && $generator_exc[%d] !== null) throw $generator_exc[%d];" % (\
                self.try_depth, self.try_depth, self.try_depth)
        self.generator_add_state()
        self.generator_switch_open()
        self.generator_switch_case(increment=False)
        if self.is_generator:
            print >> self.output, self.spacing() + "$generator_exc[%d] = null;" % (self.try_depth, )
        self.generator_switch_case(increment=True)

        for stmt in node.body.nodes:
            self._stmt(stmt, current_klass)

        self.generator_switch_case(increment=True)
        if hasattr(node, 'else_') and node.else_:
            print >> self.output, self.spacing() + "throw pyjslib['TryElse'];"
            self.generator_switch_case(increment=True)

        self.generator_switch_case(increment=True)
        self.generator_switch_close()

        print >> self.output, self.dedent() + "} catch(%s) {" % pyjs_try_err
        self.indent()
        if self.is_generator:
            print >> self.output, self.spacing() + "$generator_exc[%d] = %s;" % (self.try_depth, pyjs_try_err)
        try_state_max_depth = self.state_max_depth
        self.generator_states += [0 for i in range(save_state_max_depth+1, try_state_max_depth)]

        if hasattr(node, 'else_') and node.else_:
            print >> self.output, self.indent() + """\
if (%(e)s.__name__ == 'TryElse') {""" % {'e': pyjs_try_err}

            self.generator_add_state()
            self.generator_switch_open()
            self.generator_switch_case(increment=False)

            for stmt in node.else_:
                self._stmt(stmt, current_klass)

            self.generator_switch_case(increment=True)
            self.generator_switch_close()
            self.generator_del_state()

            print >> self.output, self.dedent() + """} else {"""
            self.indent()
        if self.attribute_checking:
            print >> self.output, self.spacing() + """%s = pyjslib['_errorMapping'](%s);""" % (pyjs_try_err, pyjs_try_err)
        print >> self.output, self.spacing() + """\
var %(e)s_name = (typeof %(e)s.__name__ == 'undefined' ? %(e)s.name : %(e)s.__name__ );\
""" % {'e': pyjs_try_err}
        print >> self.output, self.spacing() + "$pyjs.__last_exception__ = {error: %s, module: %s, try_lineno: %s};" % (pyjs_try_err, self.module_name, node.lineno)
        if self.source_tracking:
            print >>self.output, """\
%(s)ssys.save_exception_stack();
%(s)sif ($pyjs.trackstack.length > $pyjs__trackstack_size_%(d)d) {
%(s)s\t$pyjs.trackstack = $pyjs.trackstack.slice(0,$pyjs__trackstack_size_%(d)d);
%(s)s\t$pyjs.track = $pyjs.trackstack.slice(-1)[0];
%(s)s}
%(s)s$pyjs.track.module='%(m)s';""" % {'s': self.spacing(), 'd': self.stacksize_depth, 'm': self.module_name}

        pyjs_try_err = self.add_lookup('variable', pyjs_try_err, pyjs_try_err)
        if hasattr(node, 'handlers'):
            else_str = self.spacing()
            if len(node.handlers) == 1 and node.handlers[0][0] is None:
                else_str += "if (true) "
            for handler in node.handlers:
                lineno = handler[2].nodes[0].lineno
                expr = handler[0]
                as_ = handler[1]
                if as_:
                    errName = as_.name
                else:
                    errName = 'err'

                if not expr:
                    print >> self.output, "%s{" % else_str
                else:
                    if expr.lineno:
                        lineno = expr.lineno
                    l = []
                    if isinstance(expr, self.ast.Tuple):
                        for x in expr.nodes:
                            l.append("((%s_name == %s.__name__)||pyjslib['_isinstance'](%s,%s))" % (pyjs_try_err, 
                                self.expr(x, current_klass),pyjs_try_err, self.expr(x, current_klass)))
                    else:
                        l = [ "(%s_name == %s.__name__)||pyjslib['_isinstance'](%s,%s)" % (pyjs_try_err, 
                                self.expr(expr, current_klass),pyjs_try_err, self.expr(expr, current_klass)) ]
                    print >> self.output, "%sif (%s) {" % (else_str, "||".join(l))
                self.indent()
                print >> self.output, self.spacing() + "$pyjs.__last_exception__.except_lineno = %d;" % lineno
                tnode = self.ast.Assign([self.ast.AssName(errName, "OP_ASSIGN", lineno)], self.ast.Name(pyjs_try_err, lineno), lineno)
                self._assign(tnode, current_klass)

                self.generator_add_state()
                self.generator_switch_open()
                self.generator_switch_case(increment=False)

                for stmt in handler[2]:
                    self._stmt(stmt, current_klass)

                self.generator_switch_case(increment=True)
                self.generator_switch_close()
                self.generator_del_state()

                print >> self.output, self.dedent() + "}",
                else_str = "else "

            if node.handlers[-1][0]:
                # No default catcher, create one to fall through
                print >> self.output, "%s{ throw %s; }" % (else_str, pyjs_try_err)
            else:
                print >> self.output
        if hasattr(node, 'else_') and node.else_:
            print >> self.output, self.dedent() + "}"

        final = None
        if hasattr(node, 'final'):
            final = node.final
        if hasattr(node, 'final_'):
            final = node.final_

        if final is not None:
            print >>self.output, self.dedent() + "} finally {"
            self.indent()
            if self.is_generator:
                print >>self.output, self.spacing() + "if ($yielding === true) return $yield_value;"
                #print >>self.output, self.spacing() + "if ($yielding === null) throw $exc;"

            else_except_state_max_depth = self.state_max_depth
            self.generator_states = self.generator_states[:save_state_max_depth]
            self.generator_states += [0 for i in range(save_state_max_depth, else_except_state_max_depth)]
            self.generator_add_state()
            self.generator_switch_open()
            self.generator_switch_case(increment=False)

            for stmt in final:
                self._stmt(stmt, current_klass)

            self.generator_switch_case(increment=True)
            self.generator_switch_close()

        self.generator_states = self.generator_states[:start_states+1]
        print >>self.output, self.dedent()  + "}"
        if self.is_generator:
            print >> self.output, self.spacing() + "$generator_exc[%d] = null;" % (self.try_depth, )
        self.generator_clear_state()
        self.generator_del_state()
        self.try_depth -= 1
        self.stacksize_depth -= 1
        self.generator_switch_case(increment=True)
        self.is_generator = save_is_generator

    # XXX: change use_getattr to True to enable "strict" compilation
    # but incurring a 100% performance penalty. oops.
    def _getattr(self, v, current_klass, use_getattr=False):
        attr_name = self.attrib_remap(v.attrname)
        if isinstance(v.expr, self.ast.Name):
            obj = self._name(v.expr, current_klass, return_none_for_module=True)
            if not use_getattr or attr_name == '__class__' or \
                    attr_name == '__name__':
                return [obj, attr_name]
            return ["pyjslib['getattr'](%s, '%s')" % (obj, attr_name)]
        elif isinstance(v.expr, self.ast.Getattr):
            return self._getattr(v.expr, current_klass) + [attr_name]
        elif isinstance(v.expr, self.ast.Subscript):
            return [self._subscript(v.expr, self.modpfx()), attr_name]
        elif isinstance(v.expr, self.ast.CallFunc):
            return [self._callfunc(v.expr, self.modpfx()), attr_name]
        elif isinstance(v.expr, self.ast.Const):
            return [self._const(v.expr), attr_name]
        else:
            raise TranslationError(
                "unsupported type (in _getattr)", v.expr, self.module_name)


    def modpfx(self):
        return strip_py(self.module_prefix)

    def _name(self, v, current_klass, 
              return_none_for_module=False):

        if not hasattr(v, 'name'):
            name = v.attrname
        else:
            name = v.name

        name_type, pyname, jsname, depth, is_local = self.lookup(name)
        if name_type is None:
            # What to do with a (yet) unknown name?
            # Just nothing...
            return self.scopeName(name, depth, is_local)
        return jsname

    def _name2(self, v, current_klass, attr_name):
        name_type, pyname, jsname, depth, is_local = self.lookup(v.name)
        if name_type is None:
            jsname = self.scopeName(v.name, depth, is_local)
        return jsname, attr_name

    def _getattr2(self, v, current_klass, attr_name):
        if isinstance(v.expr, self.ast.Getattr):
            return self._getattr2(v.expr, current_klass, v.attrname) + [attr_name]
        if isinstance(v.expr, self.ast.Name):
            name_type, pyname, jsname, depth, is_local = self.lookup(v.expr.name)
            if name_type is None:
                jsname = self.scopeName(v.expr.name, depth, is_local)
            return [jsname, v.attrname, attr_name]
        return [self.expr(v.expr, current_klass), v.attrname, attr_name]

    def _class(self, node, parent_class = None):
        save_top_level = self.top_level
        if parent_class is None:
            class_name = self.modpfx() + node.name
        else:
            class_name = node.name
        self.top_level = False
        local_prefix = '$cls_definition'
        name_scope = {}
        current_klass = Klass(class_name, name_scope)
        current_klass.__md5__ = self.md5(node)
        if len(node.bases) == 0:
            base_classes = [("object", "pyjslib.object")]
        else:
            base_classes = []
            for node_base in node.bases:
                if isinstance(node_base, self.ast.Name):
                    node_base_name = node_base.name
                    base_class = self._name(node_base, None)
                elif isinstance(node_base, self.ast.Getattr):
                    # the bases are not in scope of the class so do not
                    # pass our class to self._name
                    node_base_name = node_base.attrname
                    base_class = self.expr(node_base, None)
                else:
                    raise TranslationError(
                        "unsupported type (in _class)",
                        node_base, self.module_name)
                base_classes.append((node_base_name, base_class))
            current_klass.set_base(base_classes[0][1])

        if node.name in ['object', 'pyjslib.Object', 'pyjslib.object']:
            base_classes = []
        class_name = self.add_lookup('class', node.name, class_name)
        print >>self.output, self.indent() + class_name + """ = (function(){
%(s)svar $cls_instance = $pyjs__class_instance('%(n)s');
%(s)svar %(p)s = new Object();
%(s)svar $method;
%(s)s%(p)s.__md5__ = '%(m)s';""" % {'s': self.spacing(), 'n': node.name, 'p': local_prefix, 'm': current_klass.__md5__}

        self.push_lookup(name_scope)
        for child in node.code:
            self.is_class_definition = True
            self.local_prefix = local_prefix
            self._stmt(child, current_klass)
        print >>self.output, """\
%(s)sreturn $pyjs__class_function($cls_instance, %(local_prefix)s, 
%(s)s                            new Array(""" % {'s': self.spacing(), 'local_prefix': local_prefix}  + ",".join(map(lambda x: x[1], base_classes)) + """));
%s})();""" % self.dedent()
        self.pop_lookup()
        self.is_class_definition = None
        self.local_prefix = None
        self.top_level = save_top_level

    def classattr(self, node, current_klass):
        self._assign(node, current_klass)

    def _raise(self, node, current_klass):
        if self.is_generator:
            print >> self.output, self.spacing() + "$generator_state[%d]=%d;" % (len(self.generator_states)-1, self.generator_states[-1]+1)

        if node.expr1:
            if node.expr2:
                if node.expr3:
                    print >> self.output, """
    %(s)svar $pyjs__raise_expr1 = %(expr1)s;
    %(s)svar $pyjs__raise_expr2 = %(expr2)s;
    %(s)svar $pyjs__raise_expr3 = %(expr3)s;
    %(s)sif ($pyjs__raise_expr2 !== null && $pyjs__raise_expr1.__is_instance__ === true) {
    %(s)s\tthrow pyjslib['TypeError']('instance exception may not have a separate value');
    %(s)s}
    %(s)s\tthrow ($pyjs__raise_expr1.apply($pyjs__raise_expr1, $pyjs__raise_expr2, $pyjs__raise_expr3));
    """ % { 's': self.spacing(),
            'expr1': self.expr(node.expr1, current_klass),
            'expr2': self.expr(node.expr2, current_klass),
            'expr3': self.expr(node.expr3, current_klass),
          }
                else:
                    print >> self.output, """
%(s)svar $pyjs__raise_expr1 = %(expr1)s;
%(s)svar $pyjs__raise_expr2 = %(expr2)s;
%(s)sif ($pyjs__raise_expr2 !== null && $pyjs__raise_expr1.__is_instance__ === true) {
%(s)s\tthrow pyjslib['TypeError']('instance exception may not have a separate value');
%(s)s}
%(s)sif (pyjslib['isinstance']($pyjs__raise_expr2, pyjslib['tuple'])) {
%(s)s\tthrow ($pyjs__raise_expr1.apply($pyjs__raise_expr1, $pyjs__raise_expr2.getArray()));
%(s)s} else {
%(s)s\tthrow ($pyjs__raise_expr1($pyjs__raise_expr2));
%(s)s}
""" % { 's': self.spacing(),
        'expr1': self.expr(node.expr1, current_klass),
        'expr2': self.expr(node.expr2, current_klass),
      }
            else:
                print >> self.output, self.spacing() + "throw (%s);" % self.expr(
                    node.expr1, current_klass)
        else:
            s = self.spacing()
            print >> self.output, """\
%(s)sthrow ($pyjs.__last_exception__?
%(s)s\t$pyjs.__last_exception__.error:
%(s)s\tpyjslib['TypeError']('exceptions must be classes, instances, or strings (deprecated), not NoneType'));\
""" % locals()
        self.generator_switch_case(increment=True)

    def _method(self, node, current_klass):
        save_top_level = self.top_level
        self.push_options()
        save_has_js_return = self.has_js_return
        self.has_js_return = False
        save_has_yield = self.has_yield
        self.has_yield = False
        save_is_generator = self.is_generator
        self.is_generator = False
        save_generator_states = self.generator_states
        self.generator_states = [0]
        self.state_max_depth = len(self.generator_states)
        save_local_prefix = self.local_prefix

        method_name = self.attrib_remap(node.name)
        jsmethod_name = self.add_lookup('method', method_name, method_name)

        self.local_prefix = None
        self.is_class_definition = None

        staticmethod, classmethod, decorator_code = self.parse_decorators(node, method_name, current_klass)

        if node.name == '__new__':
            staticmethod = True

        self.pop_lookup()
        self.push_lookup()
        arg_names = []
        for arg in node.argnames:
            if isinstance(arg, tuple):
                for a in arg:
                    arg_names.append(self.add_lookup('variable', a, a))
            else:
                arg_names.append(self.add_lookup('variable', arg, arg))

        normal_arg_names = arg_names[0:]
        if node.kwargs:
            kwargname = normal_arg_names.pop()
        else:
            kwargname = None
        if node.varargs:
            varargname = normal_arg_names.pop()
        else:
            varargname = None
        declared_arg_names = list(normal_arg_names)
        #if node.kwargs: declared_arg_names.append(kwargname)

        if staticmethod:
            function_args = "(" + ", ".join(declared_arg_names) + ")"
        else:
            function_args = "(" + ", ".join(declared_arg_names[1:]) + ")"

        print >>self.output, self.indent() + "$method = $pyjs__bind_method($cls_instance, '"+method_name+"', function" + function_args + " {"
        if staticmethod:
            self._static_method_init(node, declared_arg_names, varargname, kwargname, current_klass)
        elif classmethod:
            self._class_method_init(node, declared_arg_names, varargname, kwargname, current_klass)
        else:
            self._instance_method_init(node, declared_arg_names, varargname, kwargname, current_klass)

        # default arguments
        self._default_args_handler(node, declared_arg_names, current_klass, kwargname)

        local_arg_names = normal_arg_names + declared_arg_names

        if node.kwargs:
            local_arg_names.append(kwargname)
        if node.varargs:
            local_arg_names.append(varargname)

        self.top_level = False
        save_output = self.output
        self.output = StringIO()
        if self.source_tracking:
            print >>self.output, self.spacing() + "$pyjs.track={module:%s, lineno:%d};$pyjs.trackstack.push($pyjs.track);" % (self.module_name, node.lineno)
        self.track_lineno(node, True)
        for child in node.code:
            self._stmt(child, current_klass)
        if not self.has_yield and self.source_tracking and self.has_js_return:
            self.source_tracking = False
            self.output = StringIO()
            for child in node.code:
                self._stmt(child, None)
        elif self.has_yield:
            if self.has_js_return:
                self.source_tracking = False
            self.is_generator = True
            self.generator_states = [0]
            self.output = StringIO()
            self.indent()
            if self.source_tracking:
                print >>self.output, self.spacing() + "$pyjs.track={module:'%s',lineno:%d};$pyjs.trackstack.push($pyjs.track);" % (self.module_name, node.lineno)
            self.track_lineno(node, True)
            self.generator_switch_open()
            self.generator_switch_case(increment=False)
            for child in node.code:
                self._stmt(child, None)
            self.generator_switch_case(increment=True)
            self.generator_switch_close()
            self.dedent()

        captured_output = self.output.getvalue()
        self.output = save_output
        print >>self.output, self.local_js_vars_decl(local_arg_names)
        if self.is_generator:
            self.generator(captured_output)
        else:
            print >>self.output, captured_output,

            # we need to return null always, so it is not undefined
            if node.code.nodes:
                lastStmt = node.code.nodes[-1]
            else:
                lastStmt = None
            if not isinstance(lastStmt, self.ast.Return):
                if self.source_tracking:
                    print >>self.output, self.spacing() + "$pyjs.trackstack.pop();$pyjs.track=$pyjs.trackstack.pop();$pyjs.trackstack.push($pyjs.track);"
                if not self._isNativeFunc(lastStmt):
                    print >>self.output, self.spacing() + "return null;"

        print >>self.output, self.dedent() + "}"

        bind_type = 'bound'
        if staticmethod:
            bind_type = 'static'
        elif classmethod:
            bind_type = 'class'

        self.pop_lookup()
        self.func_args(node, current_klass, None, bind_type, declared_arg_names, varargname, kwargname)

        self.generator_states = save_generator_states
        self.state_max_depth = len(self.generator_states)
        self.is_generator = save_is_generator
        self.has_yield = save_has_yield
        self.has_js_return = save_has_js_return
        self.pop_options()

        self.push_lookup(current_klass.name_scope)
        staticmethod, classmethod, decorator_code = self.parse_decorators(node, node.name, current_klass, 
                                                                          True, bind_type)
        decorator_code = decorator_code % '$method'
        print >>self.output, self.spacing() + "%s = %s;" % (jsmethod_name, decorator_code)
        self.add_lookup('method', node.name, "pyjslib['staticmethod'](%s)" % jsmethod_name)
        self.local_prefix = save_local_prefix
        self.is_class_definition = True
        self.top_level = save_top_level


    def _isNativeFunc(self, node):
        if isinstance(node, self.ast.Discard):
            if isinstance(node.expr, self.ast.CallFunc):
                if isinstance(node.expr.node, self.ast.Name):
                    name_type, pyname, jsname, depth, is_local = self.lookup(node.expr.node.name)
                    if name_type == '__pyjamas__' and jsname == NATIVE_JS_FUNC_NAME:
                        return True
        return False

    def _stmt(self, node, current_klass):
        self.track_lineno(node)

        if isinstance(node, self.ast.Return):
            self._return(node, current_klass)
        elif isinstance(node, self.ast.Yield):
            self._yield(node, current_klass)
        elif isinstance(node, self.ast.Break):
            self._break(node, current_klass)
        elif isinstance(node, self.ast.Continue):
            self._continue(node, current_klass)
        elif isinstance(node, self.ast.Assign):
            self._assign(node, current_klass)
        elif isinstance(node, self.ast.AugAssign):
            self._augassign(node, current_klass)
        elif isinstance(node, self.ast.Discard):
            self._discard(node, current_klass)
        elif isinstance(node, self.ast.If):
            self._if(node, current_klass)
        elif isinstance(node, self.ast.For):
            self._for(node, current_klass)
        elif isinstance(node, self.ast.While):
            self._while(node, current_klass)
        elif isinstance(node, self.ast.Subscript):
            self._subscript_stmt(node, current_klass)
        elif isinstance(node, self.ast.Global):
            self._global(node, current_klass)
        elif isinstance(node, self.ast.Pass):
            pass
        elif isinstance(node, self.ast.Function):
            self._function(node, current_klass)
        elif isinstance(node, self.ast.Printnl):
           self._print(node, current_klass)
        elif isinstance(node, self.ast.Print):
           self._print(node, current_klass)
        elif isinstance(node, self.ast.TryExcept):
            self._tryExcept(node, current_klass)
        elif isinstance(node, self.ast.TryFinally):
            self._tryFinally(node, current_klass)
        elif isinstance(node, self.ast.Raise):
            self._raise(node, current_klass)
        elif isinstance(node, self.ast.Import):
            self._import(node, current_klass)
        elif isinstance(node, self.ast.From):
            self._from(node, current_klass)
        elif isinstance(node, self.ast.AssAttr):
            self._assattr(node, current_klass)
        elif isinstance(node, self.ast.Assert):
            self._assert(node, current_klass)
        elif isinstance(node, self.ast.Class):
            self._class(node, current_klass)
        #elif isinstance(node, self.ast.CallFunc):
        #    self._callfunc(node, current_klass)
        elif isinstance(node, self.ast.Slice):
            print >>self.output, self.spacing() + self._slice(node, current_klass)
        elif isinstance(node, self.ast.AssName):
            # TODO: support other OP_xxx types and move this to
            # a separate function
            if node.flags == "OP_DELETE":
                name = self._lhsFromName(node.name, current_klass)
                print >>self.output, self.spacing() + "pyjslib['_del'](%s);" % name
            else:
                raise TranslationError(
                    "unsupported AssName type (in _stmt)", node, self.module_name)
        else:
            raise TranslationError(
                "unsupported type (in _stmt)", node, self.module_name)


    def get_start_line(self, node, lineno):
        if node:
            if hasattr(node, "lineno") and node.lineno != None and node.lineno < lineno:
                lineno = node.lineno
            if hasattr(node, 'getChildren'):
                for n in node.getChildren():
                    lineno = self.get_start_line(n, lineno)
        return lineno

    def get_line_trace(self, node):
        lineNum1 = "Unknown"
        srcLine = ""
        if hasattr(node, "lineno"):
            if node.lineno != None:
                lineNum2 = node.lineno
                lineNum1 = self.get_start_line(node, lineNum2)
                srcLine = self.src[min(lineNum1, len(self.src))-1].strip()
                if lineNum1 < lineNum2:
                    srcLine += ' ... ' + self.src[min(lineNum2, len(self.src))-1].strip()
                srcLine = srcLine.replace('\\', '\\\\')
                srcLine = srcLine.replace('"', '\\"')
                srcLine = srcLine.replace("'", "\\'")

        return self.module_name + ".py, line " \
               + str(lineNum1) + ":"\
               + "\\n" \
               + "    " + srcLine

    def _augassign(self, node, current_klass):
        def astOP(op):
            if op == "+=":
                return self.ast.Add
            if op == "-=":
                return self.ast.Sub
            if op == "*=":
                return self.ast.Mul
            if op == "/=":
                return self.ast.Div
            if op == "%=":
                return self.ast.Mod
            if self.number_classes:
                if op == "&=":
                    return self.ast.Bitand
                if op == "^=":
                    return self.ast.Bitxor
                if op == "|=":
                    return self.ast.Bitor
                if op == ">>=":
                    return self.ast.RightShift
                if op == "<<=":
                    return self.ast.LeftShift
            raise TranslationError(
                 "unsupported OP (in _augassign)", node, self.module_name)
        v = node.node
        if isinstance(v, self.ast.Getattr):
            # XXX HACK!  don't allow += on return result of getattr.
            # TODO: create a temporary variable or something.
            lhs = self.attrib_join(self._getattr(v, current_klass, False))
            lhs_ass = self.ast.AssAttr(v.expr, v.attrname, "OP_ASSIGN", node.lineno)
        elif isinstance(v, self.ast.Name):
            lhs = self._name(v, current_klass)
            lhs_ass = self.ast.AssName(v.name, "OP_ASSIGN", node.lineno)
        elif isinstance(v, self.ast.Subscript) or self.operator_funcs:
            if len(v.subs) != 1:
                raise TranslationError(
                    "must have one sub (in _assign)", v, self.module_name)
            lhs = self.ast.Subscript(v.expr, "OP_ASSIGN", v.subs)
            expr = v.expr
            subs = v.subs
            if not (isinstance(v.subs[0], self.ast.Const) or \
                    isinstance(v.subs[0], self.ast.Name)) or \
               not isinstance(v.expr, self.ast.Name):
                # There's something complex here.
                # Neither a simple x[0] += ?
                # Nore a simple x[y] += ?
                augexpr = self.uniqid('$augexpr')
                augsub = self.uniqid('$augsub')
                print >>self.output, self.spacing() + "var " + augsub + " = " + self.expr(subs[0], current_klass) + ";"
                self.add_lookup('variable', augexpr, augexpr)
                print >>self.output, self.spacing() + "var " + augexpr + " = " + self.expr(expr, current_klass) + ";"
                self.add_lookup('variable', augsub, augsub)
                lhs = self.ast.Subscript(self.ast.Name(augexpr), "OP_ASSIGN", [self.ast.Name(augsub)])
                v = self.ast.Subscript(self.ast.Name(augexpr), v.flags, [self.ast.Name(augsub)])
            op = astOP(node.op)
            try: # python2.N 
                tnode = self.ast.Assign([lhs], op((v, node.expr)))
            except: # lib2to3
                tnode = self.ast.Assign([lhs], op(v, node.expr))
            return self._assign(tnode, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in _augassign)", v, self.module_name)
        try:
            op_ass = astOP(node.op)
        except:
            op_ass = None
        if not self.operator_funcs or op_ass is None:
            op = node.op
            rhs = self.expr(node.expr, current_klass)
            print >>self.output, self.spacing() + lhs + " " + op + " " + rhs + ";"
            return
        if isinstance(v, self.ast.Name):
            self.add_lookup('global', v.name, lhs)
        op = astOP(node.op)
        try: # python2.N 
            tnode = self.ast.Assign([lhs_ass], op((v, node.expr)))
        except: # lib2to3
            tnode = self.ast.Assign([lhs_ass], op(v, node.expr))
        return self._assign(tnode, current_klass)

    def _lhsFromName(self, name, current_klass, set_name_type = 'variable'):
        name_type, pyname, jsname, depth, is_local = self.lookup(name)
        if is_local:
            lhs = jsname
            self.add_lookup(set_name_type, name, jsname)
        elif self.top_level:
            if current_klass:
                lhs = current_klass.name + "." + name
            else:
                vname = self.modpfx() + name
                vname = self.add_lookup(set_name_type, name, vname)
                #lhs = "var " + name + " = " + vname
                lhs = vname
        else:
            vname = self.add_lookup(set_name_type, name, name)
            lhs = vname
        return lhs

    def _lhsFromAttr(self, v, current_klass):
        if isinstance(v.expr, self.ast.Name):
            lhs = self._name(v.expr, current_klass)
        elif isinstance(v.expr, self.ast.Getattr):
            lhs = self.attrib_join(self._getattr(v, current_klass)[:-1])
        elif isinstance(v.expr, self.ast.Subscript):
            lhs = self._subscript(v.expr, current_klass)
        elif isinstance(v.expr, self.ast.CallFunc):
            lhs = self._callfunc(v.expr, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in _assign)", v.expr, self.module_name)
        return lhs

    def _assign(self, node, current_klass):
        if len(node.nodes) != 1:
            tempvar = self.uniqid("$assign")
            tnode = self.ast.Assign([self.ast.AssName(tempvar, "OP_ASSIGN", node.lineno)], node.expr, node.lineno)
            self._assign(tnode, current_klass)
            for v in node.nodes:
               tnode2 = self.ast.Assign([v], self.ast.Name(tempvar, node.lineno), node.lineno)
               self._assign(tnode2, current_klass)
            return

        dbg = 0
        v = node.nodes[0]
        if isinstance(v, self.ast.AssAttr):
            attr_name = self.attrib_remap(v.attrname)
            rhs = self.expr(node.expr, current_klass)
            lhs = self._lhsFromAttr(v, current_klass)
            if v.flags == "OP_ASSIGN":
                op = "="
            else:
                raise TranslationError(
                    "unsupported flag (in _assign)", v, self.module_name)
            if self.descriptors:
                print >>self.output, self.spacing() + "pyjslib['setattr'](%s, '%s', %s);" % (lhs, attr_name, rhs)
                return
            lhs += '.' + attr_name

        elif isinstance(v, self.ast.AssName):
            rhs = self.expr(node.expr, current_klass)
            lhs = self._lhsFromName(v.name, current_klass)
            if v.flags == "OP_ASSIGN":
                op = "="
            else:
                raise TranslationError(
                    "unsupported flag (in _assign)", v, self.module_name)
        elif isinstance(v, self.ast.Subscript):
            if v.flags == "OP_ASSIGN":
                obj = self.expr(v.expr, current_klass)
                if len(v.subs) != 1:
                    raise TranslationError(
                        "must have one sub (in _assign)", v, self.module_name)
                idx = self.expr(v.subs[0], current_klass)
                value = self.expr(node.expr, current_klass)
                print >>self.output, self.spacing() + self.track_call(obj + ".__setitem__(" + idx + ", " + value + ")", v.lineno) + ';'
                return
            else:
                raise TranslationError(
                    "unsupported flag (in _assign)", v, self.module_name)
        elif isinstance(v, self.ast.Slice):
            if v.flags == "OP_ASSIGN":
                if not v.lower:
                    lower = 0
                else:
                    lower = self.expr(v.lower, current_klass)
                if not v.upper:
                    upper = 'null'
                else:
                    upper = self.expr(v.upper, current_klass)
                obj = self.expr(v.expr, current_klass)
                value = self.expr(node.expr, current_klass)
                print >>self.output, self.spacing() + self.track_call("pyjslib.__setslice(%s, %s, %s, %s)" % (obj, lower, upper, value), v.lineno) + ';'
                return
            else:
                raise TranslationError(
                    "unsupported flag (in _assign)", v, self.module_name)
        elif isinstance(v, (self.ast.AssList, self.ast.AssTuple)):
            tempName = self.uniqid("$tupleassign")
            print >>self.output, self.spacing() + "var " + tempName + " = " + \
                                 self.expr(node.expr, current_klass) + ";"
            for index,child in enumerate(v.getChildNodes()):
                rhs = self.track_call(tempName + ".__getitem__(" + str(index) + ")", v.lineno)

                if isinstance(child, self.ast.AssAttr):
                    lhs = self._lhsFromAttr(child, current_klass) + '.' + self.attrib_remap(child.attrname)
                elif isinstance(child, self.ast.AssName):
                    lhs = self._lhsFromName(child.name, current_klass)
                elif isinstance(child, self.ast.Subscript):
                    if child.flags == "OP_ASSIGN":
                        obj = self.expr(child.expr, current_klass)
                        if len(child.subs) != 1:
                            raise TranslationError("must have one sub " +
                                                   "(in _assign)",
                                                   child,
                                                   self.module_name)
                        idx = self.expr(child.subs[0], current_klass)
                        value = self.expr(node.expr, current_klass)
                        print >>self.output, self.spacing() + self.track_call(obj + ".__setitem__(" \
                                           + idx + ", " + rhs + ")", v.lineno) + ';'
                        continue
                print >>self.output, self.spacing() + lhs + " = " + rhs + ";"
            return
        else:
            raise TranslationError(
                "unsupported type (in _assign)", v, self.module_name)

        if dbg:
            print "b", repr(node.expr), rhs
        print >>self.output, self.spacing() + lhs + " " + op + " " + rhs + ";"

    def _discard(self, node, current_klass):
        
        if isinstance(node.expr, self.ast.CallFunc):
            expr = self._callfunc(node.expr, current_klass)
            if isinstance(node.expr.node, self.ast.Name):
                name_type, pyname, jsname, depth, is_local = self.lookup(node.expr.node.name)
                if name_type == '__pyjamas__' and jsname == NATIVE_JS_FUNC_NAME:
                    print >>self.output, expr
                    return
            print >>self.output, self.spacing() + expr + ";"

        elif isinstance(node.expr, self.ast.Const):
            # we can safely remove all constants that are discarded,
            # e.g None fo empty expressions after a unneeded ";" or
            # mostly important to remove doc strings
            if node.expr.value in ["@CONSTANT_DECLARATION@"]:
                print >>self.output, node.expr.value
            return
        elif isinstance(node.expr, self.ast.Yield):
            self._yield(node.expr, current_klass)
        else:
            raise TranslationError(
                "unsupported type, must be call or const (in _discard)", node.expr,  self.module_name)


    def _if(self, node, current_klass):
        save_is_generator = self.is_generator
        if self.is_generator:
            self.is_generator = self.compiler.walk(node, GeneratorExitVisitor(), walker=GeneratorExitVisitor()).has_yield
        if self.is_generator:
            print >>self.output, self.spacing() + "$generator_state[%d] = 0;" % (len(self.generator_states)+1,)
            self.generator_switch_case(increment=True)
            self.generator_add_state()
        for i in range(len(node.tests)):
            test, consequence = node.tests[i]
            if i == 0:
                keyword = "if"
            else:
                keyword = "else if"

            self.lookup_stack[-1]
            self._if_test(keyword, test, consequence, node, current_klass)

        if node.else_:
            keyword = "else"
            test = None
            consequence = node.else_

            self._if_test(keyword, test, consequence, node, current_klass)
        if self.is_generator:
            print >>self.output, self.spacing() + "$generator_state[%d]=0;" % (len(self.generator_states)-1,)
        self.generator_del_state()
        self.is_generator = save_is_generator

    def _if_test(self, keyword, test, consequence, node, current_klass):
        if test:
            expr = self.expr(test, current_klass)

            if not self.is_generator:
                print >>self.output, self.indent() +keyword + " (" + self.track_call(self.inline_bool_code(expr), test.lineno)+") {"
            else:
                self.generator_states[-1] += 1
                print >>self.output, self.indent() +keyword + "(($generator_state[%d]==%d)||($generator_state[%d]<%d&&(" % (\
                    len(self.generator_states)-1, self.generator_states[-1], len(self.generator_states)-1, self.generator_states[-1],) + \
                    self.track_call(self.inline_bool_code(expr), test.lineno)+"))) {"
                print >>self.output, self.spacing() + "$generator_state[%d]=%d;" % (len(self.generator_states)-1, self.generator_states[-1])

        else:
            if not self.is_generator:
                print >>self.output, self.indent() + keyword + " {"
            else:
                self.generator_states[-1] += 1
                print >>self.output, self.indent() + keyword + " if ($generator_state[%d]==0||$generator_state[%d]==%d) {" % (\
                    len(self.generator_states)-1, len(self.generator_states)-1, self.generator_states[-1], )
                print >>self.output, self.spacing() + "$generator_state[%d]=%d;" % (len(self.generator_states)-1, self.generator_states[-1])

        if self.is_generator:
            self.generator_add_state()
            self.generator_switch_open()
            self.generator_switch_case(increment=False)

        if isinstance(consequence, self.ast.Stmt):
            for child in consequence.nodes:
                self._stmt(child, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in _if_test)", consequence,  self.module_name)

        if self.is_generator:
            self.generator_switch_case(increment=True)
            self.generator_switch_close()
            self.generator_del_state()

        print >>self.output, self.dedent() + "}"

    def _compare(self, node, current_klass):
        lhs = self.expr(node.expr, current_klass)

        if len(node.ops) != 1:
            cmp = []
            for op, rhs_node in node.ops:
                rhsname = self.uniqid("$compare")
                rhs = self.expr(rhs_node, current_klass)
                rhs = "(%s = %s)" % (rhsname, rhs)
                cmp.append(self.compare_code(op, lhs, rhs))
                lhs = rhsname
            return "(%s)" % "&&".join(cmp)
            raise TranslationError(
                "only one ops supported (in _compare)", node,  self.module_name)

        op = node.ops[0][0]
        rhs_node = node.ops[0][1]
        rhs = self.expr(rhs_node, current_klass)
        return self.compare_code(op, lhs, rhs)

    def compare_code(self, op, lhs, rhs):
        if op == "==":
            return self.inline_eq_code(lhs, rhs)
        if op == "!=":
            return "!"+self.inline_eq_code(lhs, rhs)
        if op == "<":
            return "(%s == -1)" % self.inline_cmp_code(lhs, rhs)
        if op == "<=":
            return "(%s < 1)" % self.inline_cmp_code(lhs, rhs)
        if op == ">":
            return "(%s == 1)" % self.inline_cmp_code(lhs, rhs)
        if op == ">=":
            return "(((%s)|1) == 1)" % self.inline_cmp_code(lhs, rhs)
        if op == "in":
            return rhs + ".__contains__(" + lhs + ")"
        elif op == "not in":
            return "!" + rhs + ".__contains__(" + lhs + ")"
        if op == "is":
            if self.number_classes:
                return "pyjslib['op_is'](%s, %s)" % (lhs, rhs)
            op = "==="
        if op == "is not":
            if self.number_classes:
                return "!pyjslib['op_is'](%s, %s)" % (lhs, rhs)
            op = "!=="

        return "(" + lhs + " " + op + " " + rhs + ")"


    def _not(self, node, current_klass):
        expr = self.expr(node.expr, current_klass)
        return "!" + self.inline_bool_code(expr)

    def _or(self, node, current_klass):
        s = self.spacing()
        expr = "@EXPR@"
        for e in [self.expr(child, current_klass) for child in node.nodes[:-1]]:
            v = self.uniqid('$or')
            self.add_lookup('variable', v, v)
            bool = self.inline_bool_code("%(v)s=%(e)s" % locals())
            expr = expr.replace('@EXPR@', "(%(bool)s?%(v)s:@EXPR@)" % locals())
        v = self.uniqid('$or')
        self.add_lookup('variable', v, v)
        return  expr.replace('@EXPR@', self.expr(node.nodes[-1], current_klass))
        expr = ",".join([self.expr(child, current_klass) for child in node.nodes])
        return "pyjslib['op_or']([%s])" % expr

    def _and(self, node, current_klass):
        s = self.spacing()
        expr = "@EXPR@"
        for e in [self.expr(child, current_klass) for child in node.nodes[:-1]]:
            v = self.uniqid('$and')
            self.add_lookup('variable', v, v)
            bool = self.inline_bool_code("%(v)s=%(e)s" % locals())
            expr = expr.replace('@EXPR@', "(%(bool)s?@EXPR@:%(v)s)" % locals())
        v = self.uniqid('$and')
        self.add_lookup('variable', v, v)
        return  expr.replace('@EXPR@', self.expr(node.nodes[-1], current_klass))
        expr = ",".join([self.expr(child, current_klass) for child in node.nodes])
        return "pyjslib['op_and']([%s])" % expr

    def _for(self, node, current_klass):
        save_is_generator = self.is_generator
        if self.is_generator:
            self.is_generator = self.compiler.walk(node, GeneratorExitVisitor(), walker=GeneratorExitVisitor()).has_yield
        assign_name = ""
        assign_tuple = []
        iterid = self.uniqid('$iter')
        iterator_name = "%s_iter" % iterid
        self.add_lookup('variable', iterator_name, iterator_name)
        nextval = "%s_nextval" % iterid
        self.add_lookup('variable', nextval, nextval)
        gentype = "%s_type" % iterid
        self.add_lookup('variable', gentype, gentype)
        array = "%s_array" % iterid
        self.add_lookup('variable', array, array)
        loopvar = "%s_idx" % iterid
        self.add_lookup('variable', loopvar, loopvar)
        if node.else_:
            testvar = "%s_test" % iterid
            self.add_lookup('variable', testvar, testvar)
            assTestvar = "%s_test = " % iterid
        else:
            assTestvar = ""
        reuse_tuple = "false"

        if isinstance(node.assign, self.ast.AssName):
            assign_name = self.add_lookup('variable', node.assign.name, node.assign.name)
            if node.assign.flags == "OP_ASSIGN":
                op = "="
        elif isinstance(node.assign, self.ast.AssTuple):
            reuse_tuple = "true"
            op = "="
            i = 0
            for child in node.assign:
                child_name = child.name
                self.add_lookup('variable', child_name, child_name)
                child_name = self.add_lookup('variable', child_name, child_name)
                assign_tuple.append("""%(child_name)s %(op)s %(nextval)s.__array[%(i)i];""" % locals())
                i += 1
        else:
            raise TranslationError(
                "unsupported type (in _for)", node.assign, self.module_name)

        if isinstance(node.list, self.ast.Name):
            list_expr = self._name(node.list, current_klass)
        elif isinstance(node.list, self.ast.Getattr):
            list_expr = self.attrib_join(self._getattr(node.list, current_klass))
        elif isinstance(node.list, self.ast.CallFunc):
            list_expr = self._callfunc(node.list, current_klass)
        elif isinstance(node.list, self.ast.Subscript):
            list_expr = self._subscript(node.list, current_klass)
        elif isinstance(node.list, self.ast.Const):
            list_expr = self._const(node.list)
        elif isinstance(node.list, self.ast.List):
            list_expr = self._list(node.list, current_klass)
        elif isinstance(node.list, self.ast.Slice):
            list_expr = self._slice(node.list, current_klass)
        elif isinstance(node.list, self.ast.ListComp):
            list_expr = self._listcomp(node.list, current_klass)
        elif isinstance(node.list, self.ast.Tuple):
            list_expr = self._tuple(node.list, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in _for)", node.list, self.module_name)

        if not assign_tuple:
            assign_name = self.add_lookup('variable', assign_name, assign_name)

        if self.source_tracking:
            self.stacksize_depth += 1
            var_trackstack_size = "$pyjs__trackstack_size_%d" % self.stacksize_depth
            self.add_lookup('variable', var_trackstack_size, var_trackstack_size)
            print >>self.output, self.spacing() + "%s=$pyjs.trackstack.length;" % var_trackstack_size
        s = self.spacing()
        print >>self.output, """\
%(s)s%(iterator_name)s = """ % locals() + self.track_call("%(list_expr)s" % locals(), node.lineno) + ';'
        print >>self.output, """\
%(s)sif (typeof (%(array)s = %(iterator_name)s.__array) != 'undefined') {
%(s)s\t%(gentype)s = 0;
%(s)s} else {
%(s)s\t%(iterator_name)s = %(iterator_name)s.__iter__();
%(s)s\t%(gentype)s = typeof (%(array)s = %(iterator_name)s.__array) != 'undefined'? 0 : (typeof %(iterator_name)s.$genfunc == 'function'? 1 : -1);
%(s)s}
%(s)s%(loopvar)s = 0;""" % locals()
        condition = "typeof (%(nextval)s=(%(gentype)s?(%(gentype)s > 0?%(iterator_name)s.next(true,%(reuse_tuple)s):pyjslib['wrapped_next'](%(iterator_name)s)):%(array)s[%(loopvar)s++])) != 'undefined'" % locals()

        self.generator_switch_case(increment=True)

        if self.is_generator:
            print >>self.output, self.spacing() + "$generator_state[%d] = 0;" % (len(self.generator_states), )
            self.generator_switch_case(increment=True)
            print >>self.output, self.indent() + "for (;%s($generator_state[%d] > 0 || %s);$generator_state[%d] = 0) {" % (assTestvar, len(self.generator_states), condition, len(self.generator_states), )
        else:
            print >>self.output, self.indent() + """while (%s%s) {""" % (assTestvar, condition)
        self.generator_add_state()
        self.generator_switch_open()
        self.generator_switch_case(increment=False)

        if not assign_tuple:
            print >>self.output, self.spacing() + """%(assign_name)s %(op)s %(nextval)s;""" % locals()
        else:
            for line in assign_tuple:
                print >>self.output, self.spacing() + line

        for n in node.body.nodes:
            self._stmt(n, current_klass)

        self.generator_switch_case(increment=True)
        self.generator_switch_close()
        self.generator_del_state()

        print >>self.output, self.dedent() + "}"

        if node.else_:
            self.generator_switch_case(increment=True)
            print >>self.output, self.indent() + "if (!%(testvar)s) {" % locals()
            for n in node.else_.nodes:
                self._stmt(n, current_klass)
            print >>self.output, self.dedent() + "}"


        if self.source_tracking:
            print >>self.output, """\
%(s)sif ($pyjs.trackstack.length > $pyjs__trackstack_size_%(d)d) {
%(s)s\t$pyjs.trackstack = $pyjs.trackstack.slice(0,$pyjs__trackstack_size_%(d)d);
%(s)s\t$pyjs.track = $pyjs.trackstack.slice(-1)[0];
%(s)s}
%(s)s$pyjs.track.module='%(m)s';""" % {'s': self.spacing(), 'd': self.stacksize_depth, 'm': self.module_name}
            self.stacksize_depth -= 1
        self.generator_switch_case(increment=True)
        self.is_generator = save_is_generator

    def _while(self, node, current_klass):
        save_is_generator = self.is_generator
        if self.is_generator:
            self.is_generator = self.compiler.walk(node, GeneratorExitVisitor(), walker=GeneratorExitVisitor()).has_yield
        test = self.expr(node.test, current_klass)
        if self.is_generator:
            self.generator_switch_case(increment=True)
            self.generator_reset_state()
            self.generator_switch_case(increment=True)
            print >>self.output, self.indent() + "for (;($generator_state[%d] > 0)||(" % (\
                (len(self.generator_states),)) + \
                self.track_call(self.inline_bool_code(test), node.lineno) + ");$generator_state[%d] = 0) {" % (len(self.generator_states), )

            self.generator_add_state()
            self.generator_switch_open()
            self.generator_switch_case(increment=False)
        else:
            print >>self.output, self.indent() + "while (" + self.track_call(self.inline_bool_code(test), node.lineno) + ") {"

        if isinstance(node.body, self.ast.Stmt):
            for child in node.body.nodes:
                self._stmt(child, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in _while)", node.body, self.module_name)

        if self.is_generator:
            self.generator_switch_case(increment=True)
            self.generator_switch_close()
            self.generator_del_state()

        print >>self.output, self.dedent() + "}"
        self.generator_switch_case(increment=True)
        self.is_generator = save_is_generator


    def _const(self, node):
        if isinstance(node.value, int):
            if not self.number_classes:
                return str(node.value)
            self.constant_int[node.value] = 1
            return "$constant_int_%s" % str(node.value)
        elif isinstance(node.value, long):
            v = str(node.value)
            if v[-1] == 'L':
                v = v[:-1]
            if not self.number_classes:
                return v
            self.constant_long[node.value] = 1
            return "$constant_long_%s" % v
        elif isinstance(node.value, float):
            return str(node.value)
        elif isinstance(node.value, basestring):
            v = node.value
            if isinstance(node.value, unicode):
                v = v.encode('utf-8')
            return  "String('%s')" % escapejs(v)
        elif node.value is None:
            return "null"
        else:
            raise TranslationError(
                "unsupported type (in _const)", node, self.module_name)

    def _unaryadd(self, node, current_klass):
        if not self.operator_funcs:
            return "(%s)" % self.expr(node.expr, current_klass)
        e = self.expr(node.expr, current_klass)
        v = self.uniqid('$uadd')
        s = self.spacing()
        return """(typeof (%(v)s=%(e)s)=='number'?
%(s)s\t%(v)s:
%(s)s\tpyjslib['op_uadd'](%(v)s))""" % locals()

    def _unarysub(self, node, current_klass):
        if not self.operator_funcs:
            return "-(%s)" % self.expr(node.expr, current_klass)
        e = self.expr(node.expr, current_klass)
        v = self.uniqid('$usub')
        s = self.spacing()
        return """(typeof (%(v)s=%(e)s)=='number'?
%(s)s\t-%(v)s:
%(s)s\tpyjslib['op_usub'](%(v)s))""" % locals()

    def _add(self, node, current_klass):
        if not self.operator_funcs:
            return "(%s)+(%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$add')
        v2 = self.uniqid('$add')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && (typeof %(v1)s=='number'||typeof %(v1)s=='string')?
%(s)s\t%(v1)s+%(v2)s:
%(s)s\tpyjslib['op_add'](%(v1)s,%(v2)s))""" % locals()

    def _sub(self, node, current_klass):
        if not self.operator_funcs:
            return "(%s)-(%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$sub')
        v2 = self.uniqid('$sub')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && (typeof %(v1)s=='number'||typeof %(v1)s=='string')?
%(s)s\t%(v1)s-%(v2)s:
%(s)s\tpyjslib['op_sub'](%(v1)s,%(v2)s))""" % locals()

    def _floordiv(self, node, current_klass):
        if not self.operator_funcs:
            return "Math.floor(%s/%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$floordiv')
        v2 = self.uniqid('$floordiv')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && typeof %(v1)s=='number' && %(v2)s !== 0?
%(s)s\tMath.floor(%(v1)s/%(v2)s):
%(s)s\tpyjslib['op_floordiv'](%(v1)s,%(v2)s))""" % locals()

    def _div(self, node, current_klass):
        if not self.operator_funcs:
            return "(%s)/(%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$div')
        v2 = self.uniqid('$div')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && typeof %(v1)s=='number' && %(v2)s !== 0?
%(s)s\t%(v1)s/%(v2)s:
%(s)s\tpyjslib['op_div'](%(v1)s,%(v2)s))""" % locals()

    def _mul(self, node, current_klass):
        if not self.operator_funcs:
            return "(%s)*(%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$mul')
        v2 = self.uniqid('$mul')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && typeof %(v1)s=='number'?
%(s)s\t%(v1)s*%(v2)s:
%(s)s\tpyjslib['op_mul'](%(v1)s,%(v2)s))""" % locals()

    def _mod(self, node, current_klass):
        if isinstance(node.left, self.ast.Const) and isinstance(node.left.value, StringType):
            return self.track_call("pyjslib['sprintf']("+self.expr(node.left, current_klass) + ", " + self.expr(node.right, current_klass)+")", node.lineno)
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$mod')
        v2 = self.uniqid('$mod')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        if not self.operator_funcs:
            return """((%(v1)s=%(e1)s)!=null && (%(v2)s=%(e2)s)!=null && typeof %(v1)s=='string'?
%(s)s\tpyjslib['sprintf'](%(v1)s,%(v2)s):
%(s)s\t%(v1)s%%%(v2)s)""" % locals()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && typeof %(v1)s=='number'?
%(s)s\t%(v1)s%%%(v2)s:
%(s)s\tpyjslib['op_mod'](%(v1)s,%(v2)s))""" % locals()

    def _power(self, node, current_klass):
        if not self.operator_funcs:
            return "Math.pow(%s,%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        e1 = self.expr(node.left, current_klass)
        e2 = self.expr(node.right, current_klass)
        v1 = self.uniqid('$pow')
        v2 = self.uniqid('$pow')
        self.add_lookup('variable', v1, v1)
        self.add_lookup('variable', v2, v2)
        s = self.spacing()
        return """(typeof (%(v1)s=%(e1)s)==typeof (%(v2)s=%(e2)s) && typeof %(v1)s=='number'?
%(s)s\tMath.pow(%(v1)s,%(v2)s):
%(s)s\tpyjslib['op_pow'](%(v1)s,%(v2)s))""" % locals()

    def _invert(self, node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "~(%s)" % self.expr(node.expr, current_klass)
        return "pyjslib['op_invert'](%s)" % self.expr(node.expr, current_klass)

    def _bitshiftleft(self, node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "(%s)<<(%s)"% (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        return "pyjslib['op_bitshiftleft'](%s,%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))

    def _bitshiftright(self, node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "(%s)>>(%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))
        return "pyjslib['op_bitshiftright'](%s,%s)" % (self.expr(node.left, current_klass), self.expr(node.right, current_klass))

    def _bitand(self, node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "(%s)" % ")&(".join([self.expr(child, current_klass) for child in node.nodes])
        if len(node.nodes) == 2:
            return "pyjslib['op_bitand2'](%s, %s)" % (self.expr(node.nodes[0], current_klass), self.expr(node.nodes[1], current_klass))
        return "pyjslib['op_bitand']([%s])" % ", ".join([self.expr(child, current_klass) for child in node.nodes])

    def _bitxor(self,node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "(%s)" % ")^(".join([self.expr(child, current_klass) for child in node.nodes])
        if len(node.nodes) == 2:
            return "pyjslib['op_bitxor2'](%s, %s)" % (self.expr(node.nodes[0], current_klass), self.expr(node.nodes[1], current_klass))
        return "pyjslib['op_bitxor']([%s])" % ", ".join([self.expr(child, current_klass) for child in node.nodes])

    def _bitor(self, node, current_klass):
        if not self.operator_funcs or not self.number_classes:
            return "(%s)" % ")|(".join([self.expr(child, current_klass) for child in node.nodes])
        if len(node.nodes) == 2:
            return "pyjslib['op_bitor2'](%s, %s)" % (self.expr(node.nodes[0], current_klass), self.expr(node.nodes[1], current_klass))
        return "pyjslib['op_bitor']([%s])" % ", ".join([self.expr(child, current_klass) for child in node.nodes])

    def _subscript(self, node, current_klass):
        if node.flags == "OP_APPLY":
            if len(node.subs) == 1:
                return self.inline_getitem_code(self.expr(node.expr, current_klass), self.expr(node.subs[0], current_klass))
            else:
                raise TranslationError(
                    "must have one sub (in _subscript)", node, self.module_name)
        else:
            raise TranslationError(
                "unsupported flag (in _subscript)", node, self.module_name)

    def _subscript_stmt(self, node, current_klass):
        if node.flags == "OP_DELETE":
            print >>self.output, self.spacing() + self.track_call(self.expr(node.expr, current_klass) + ".__delitem__(" + self.expr(node.subs[0], current_klass) + ")", node.lineno) + ';'
        else:
            raise TranslationError(
                "unsupported flag (in _subscript)", node, self.module_name)

    def _assattr(self, node, current_klass):
        attr_name = self.attrib_remap(node.attrname)
        lhs = self._lhsFromAttr(node, current_klass)
        if node.flags == "OP_DELETE":
            print >>self.output, self.spacing() + "pyjslib['delattr'](%s, '%s');" % (lhs, attr_name)
        else:
            raise TranslationError(
                "unsupported flag (in _assign)", v, self.module_name)

    def _assname(self, node, current_klass):
        name_type, pyname, jsname, depth, is_local = self.lookup(node.name)
        if node.flags == "OP_DELETE":
            print >>self.output, self.spacing() + "delete %s;" % (jsname,)
        else:
            raise TranslationError(
                "unsupported flag (in _assign)", v, self.module_name)

    def _list(self, node, current_klass):
        return self.track_call("pyjslib['list']([" + ", ".join([self.expr(x, current_klass) for x in node.nodes]) + "])", node.lineno)

    def _dict(self, node, current_klass):
        items = []
        for x in node.items:
            key = self.expr(x[0], current_klass)
            value = self.expr(x[1], current_klass)
            items.append("[" + key + ", " + value + "]")
        return self.track_call("pyjslib['dict']([" + ", ".join(items) + "])")

    def _tuple(self, node, current_klass):
        return self.track_call("pyjslib['tuple']([" + ", ".join([self.expr(x, current_klass) for x in node.nodes]) + "])", node.lineno)

    def _lambda(self, node, current_klass):
        save_local_prefix, self.local_prefix = self.local_prefix, None
        save_is_class_definition, self.is_class_definition = self.is_class_definition, False
        
        function_name = self.uniqid("$lambda")
        print >> self.output, self.spacing(), "var",
        code_node = self.ast.Stmt([self.ast.Return(node.code, node.lineno)], node.lineno)
        try: # python2.N
            func_node = self.ast.Function(None, function_name, node.argnames, node.defaults, node.flags, None, code_node, node.lineno)
        except: # lib2to3
            func_node = self.ast.Function(None, function_name, node.argnames, node.defaults, node.varargs, node.kwargs, None, code_node, node.lineno)
        self._function(func_node, current_klass, True)
        
        self.local_prefix = save_local_prefix
        self.is_class_definition = save_is_class_definition
        
        return function_name

    def _listcomp(self, node, current_klass):
        self.push_lookup()
        resultlist = self.uniqid("$listcomp")
        self.add_lookup('variable', resultlist, resultlist)
        save_output = self.output
        self.output = StringIO()
        print >> self.output, "function(){"
        print >> self.output, "var %s = pyjslib['list']();" % resultlist

        tnode = self.ast.Discard(self.ast.CallFunc(self.ast.Getattr(self.ast.Name(resultlist), 'append'), [node.expr], None, None))
        for qual in node.quals[::-1]:
            if len(qual.ifs) > 1:
                raise TranslationError(
                    "unsupported ifs (in _listcomp)", node, self.module_name)
            tassign = qual.assign
            tlist = qual.list
            tbody = self.ast.Stmt([tnode])
            if len(qual.ifs) == 1:
                tbody = self.ast.Stmt([self.ast.If([(qual.ifs[0].test, tbody)], None, qual.ifs[0].lineno)])
            telse_ = None
            tnode = self.ast.For(tassign, tlist, tbody, telse_, node.lineno)
        self._for(tnode, current_klass)

        print >> self.output, "return %s;}()" % resultlist,
        captured_output = self.output
        self.output = save_output
        self.pop_lookup()
        return captured_output.getvalue()

    def _genexpr(self, node, current_klass):
        save_has_yield = self.has_yield
        self.has_yield = True
        save_is_generator = self.is_generator
        self.is_generator = True
        save_generator_states = self.generator_states
        self.generator_states = [0]
        self.state_max_depth = len(self.generator_states)
        self.push_options()
        self.source_tracking = self.debug = False

        if not isinstance(node.code, self.ast.GenExprInner):
            raise TranslationError(
                "unsupported code (in _genexpr)", node, self.module_name)
        if node.argnames != ['.0']:
            raise TranslationError(
                "argnames not supported (in _genexpr)", node, self.module_name)
        if node.kwargs:
            raise TranslationError(
                "kwargs not supported (in _genexpr)", node, self.module_name)
        if node.varargs:
            raise TranslationError(
                "varargs not supported (in _genexpr)", node, self.module_name)
        save_output = self.output
        self.output = StringIO()
        self.indent()
        self.generator_switch_open()
        self.generator_switch_case(increment=False)
        tnode = self.ast.Yield(node.code.expr, node.lineno)
        for qual in node.code.quals[::-1]:
            if isinstance(qual, self.ast.GenExprFor):
                if len(qual.ifs) > 1:
                    raise TranslationError(
                        "unsupported ifs (in _genexpr)", node.code, self.module_name)
                tassign = qual.assign
                titer = qual.iter
                tbody = self.ast.Stmt([tnode])
                tis_outmost = qual.is_outmost
                if len(qual.ifs) == 1:
                    tbody = self.ast.Stmt([self.ast.If([(qual.ifs[0].test, tbody)], None, qual.ifs[0].lineno)])
                telse_ = None
                tnode = self.ast.For(tassign, titer, tbody, telse_, node.lineno)
                self._for(tnode, current_klass)
            else:
                raise TranslationError(
                    "unsupported quals (in _genexpr)", node.code, self.module_name)
        self.generator_switch_case(increment=True)
        self.generator_switch_close()

        captured_output = self.output.getvalue()
        self.output = StringIO()
        print >> self.output, "function(){"
        self.generator(captured_output)
        print >> self.output, self.dedent() + "}()"
        captured_output = self.output.getvalue()
        self.output = save_output
        self.generator_states = save_generator_states
        self.state_max_depth = len(self.generator_states)
        self.is_generator = save_is_generator
        self.has_yield = save_has_yield
        self.pop_options()
        return captured_output

    def _slice(self, node, current_klass):
        lower = "0"
        upper = "null"
        if node.lower != None:
            lower = self.expr(node.lower, current_klass)
        if node.upper != None:
            upper = self.expr(node.upper, current_klass)
        if node.flags == "OP_APPLY":
            return  "pyjslib['slice'](" + self.expr(node.expr, current_klass) + ", " + lower + ", " + upper + ")"
        elif node.flags == "OP_DELETE":
            return  "pyjslib['__delslice'](" + self.expr(node.expr, current_klass) + ", " + lower + ", " + upper + ");"
        else:
            raise TranslationError(
                "unsupported flag (in _slice)", node, self.module_name)

    def _global(self, node, current_klass):
        for name in node.names:
            name_type, pyname, jsname, depth, is_local = self.lookup(name)
            if name_type is None:
                # Not defined yet.
                name_type = 'variable'
                pyname = name
                jsname = self.scopeName(name, depth, is_local)
            else:
                name_type = 'global'
            self.add_lookup(name_type, pyname, jsname)

    def _if_expr(self, node, current_klass):
        test = self.expr(node.test, current_klass)
        then = self.expr(node.then, current_klass)
        else_ = self.expr(node.else_, current_klass)
        return "(" + self.inline_bool_code(test) + "? (%(then)s) : (%(else_)s))" % locals()

    def _backquote(self, node, current_klass):
        return "pyjslib.repr(%s)" % self.expr(node.expr, current_klass)

    def expr(self, node, current_klass):
        if isinstance(node, self.ast.Const):
            return self._const(node)
        # @@@ not sure if the parentheses should be here or in individual operator functions - JKT
        elif isinstance(node, self.ast.Mul):
            return self._mul(node, current_klass)
        elif isinstance(node, self.ast.Add):
            return self._add(node, current_klass)
        elif isinstance(node, self.ast.Sub):
            return self._sub(node, current_klass)
        elif isinstance(node, self.ast.Div):
            return self._div(node, current_klass)
        elif isinstance(node, self.ast.FloorDiv):
            return self._floordiv(node, current_klass)
        elif isinstance(node, self.ast.Mod):
            return self._mod(node, current_klass)
        elif isinstance(node, self.ast.Power):
            return self._power(node, current_klass)
        elif isinstance(node, self.ast.UnaryAdd):
            return self._unaryadd(node, current_klass)
        elif isinstance(node, self.ast.UnarySub):
            return self._unarysub(node, current_klass)
        elif isinstance(node, self.ast.Not):
            return self._not(node, current_klass)
        elif isinstance(node, self.ast.Or):
            return self._or(node, current_klass)
        elif isinstance(node, self.ast.And):
            return self._and(node, current_klass)
        elif isinstance(node, self.ast.Invert):
            return self._invert(node, current_klass)
        elif isinstance(node,self.ast.LeftShift):
            return self._bitshiftleft(node, current_klass)
        elif isinstance(node, self.ast.RightShift):
            return self._bitshiftright(node, current_klass)
        elif isinstance(node, self.ast.Bitand):
            return self._bitand(node, current_klass)
        elif isinstance(node, self.ast.Bitxor):
            return self._bitxor(node, current_klass)
        elif isinstance(node, self.ast.Bitor):
            return self._bitor(node, current_klass)
        elif isinstance(node, self.ast.Compare):
            return self._compare(node, current_klass)
        elif isinstance(node, self.ast.CallFunc):
            return self._callfunc(node, current_klass)
        elif isinstance(node, self.ast.Name):
            return self._name(node, current_klass)
        elif isinstance(node, self.ast.Subscript):
            return self._subscript(node, current_klass)
        elif isinstance(node, self.ast.Getattr):
            attr_ = self._getattr(node, current_klass)
            attr = self.attrib_join(attr_)
            attr_left = self.attrib_join(attr_[:-1])
            attr_right = attr_[-1]
            v = self.uniqid('$attr')
            vl = self.uniqid('$attr')
            self.add_lookup('variable', v, v)
            self.add_lookup('variable', vl, vl)
            if self.bound_methods or self.descriptors:
                if not self.descriptors:
                    getattr_condition = "((%(v)s=%(attr)s) !== null & (%(vl)s=%(attr_left)s).__is_instance__) && typeof %(v)s == 'function'"
                else:
                    getattr_condition = """((%(v)s=%(attr)s) !== null & ((%(vl)s=%(attr_left)s).__is_instance__) && typeof %(v)s == 'function') ||
(%(vl)s['%(attr_right)s'] !== null && typeof %(vl)s['%(attr_right)s']['__get__'] == 'function')"""
                attr_code = """\
(""" + getattr_condition + """?
\tpyjslib['getattr'](%(vl)s, '%(attr_right)s'):
\t%(attr)s)\
"""
                attr_code = ('\n'+self.spacing()+"\t\t").join(attr_code.split('\n'))
            else:
                attr_code = "%(attr)s"
            attr_code = attr_code % locals()
            s = self.spacing()

            if not self.attribute_checking:
                attr = attr_code
            else:
                if attr.find('(') < 0 and not self.debug:
                    attrstr = attr.replace("\n", "\n\\")
                    attr = """(typeof %(attr)s=='undefined'?
%(s)s\t\t(function(){throw TypeError("%(attrstr)s is undefined");})():
%(s)s\t\t%(attr_code)s)""" % locals()
                else:
                    attr_ = attr
                    if self.source_tracking or self.debug:
                        _source_tracking = self.source_tracking
                        _debug = self.debug
                        _attribute_checking = self.attribute_checking
                        self.attribute_checking = self.source_tracking = self.debug = False
                        attr_ = self.attrib_join(self._getattr(node, current_klass))
                        self.source_tracking = _source_tracking
                        self.debug = _debug
                        self.attribute_checking = _attribute_checking
                    attrstr = attr_.replace("\n", "\\\n")
                    attr = """(function(){
%(s)s\tvar $pyjs__testval=%(attr_code)s;
%(s)s\treturn (typeof $pyjs__testval=='undefined'?
%(s)s\t\t(function(){throw TypeError(\"%(attrstr)s is undefined");})():
%(s)s\t\t$pyjs__testval);
%(s)s})()""" % locals()
            return attr
        elif isinstance(node, self.ast.List):
            return self._list(node, current_klass)
        elif isinstance(node, self.ast.Dict):
            return self._dict(node, current_klass)
        elif isinstance(node, self.ast.Tuple):
            return self._tuple(node, current_klass)
        elif isinstance(node, self.ast.Slice):
            return self._slice(node, current_klass)
        elif isinstance(node, self.ast.Lambda):
            return self._lambda(node, current_klass)
        elif isinstance(node, self.ast.ListComp):
            return self._listcomp(node, current_klass)
        elif isinstance(node, self.ast.IfExp):
            return self._if_expr(node, current_klass)
        elif isinstance(node, self.ast.Yield):
            return self._yield_expr(node, current_klass)
        elif isinstance(node, self.ast.Backquote):
            return self._backquote(node, current_klass)
        elif isinstance(node, self.ast.GenExpr):
            return self._genexpr(node, current_klass)
        else:
            raise TranslationError(
                "unsupported type (in expr)", node, self.module_name)

def import_compiler(internal_ast):

    if internal_ast:
        from lib2to3 import compiler
    else:
        import compiler

    return compiler

def translate(compiler, sources, output_file, module_name=None,
              debug=False,
              print_statements = True,
              function_argument_checking=True,
              attribute_checking=True,
              bound_methods=True,
              descriptors=True,
              source_tracking=True,
              line_tracking=True,
              store_source=True,
              inline_code=False,
              operator_funcs=True,
              number_classes=True,
             ):

    sources = map(os.path.abspath, sources)
    output_file = os.path.abspath(output_file)
    if not module_name:
        module_name, extension = os.path.splitext(os.path.basename(sources[0]))

    trees = []
    tree= None
    for src in sources:
        current_tree = compiler.parseFile(src)
        flags = set()
        f = file(src)
        for l in f:
            if l.startswith('#@PYJS_'):
                flags.add(l.strip()[7:])
        f.close()
        if tree:
            tree = merge(compiler.ast, module_name, tree, current_tree, flags)
        else:
            tree = current_tree
    #XXX: if we have an override the sourcefile and the tree is not the same!
    f = file(sources[0], "r")
    src = f.read()
    f.close()
    output = file(output_file, 'w')

    t = Translator(compiler,
                   module_name, sources[0], src, tree, output,
                   debug = debug,
                   print_statements = print_statements,
                   function_argument_checking = function_argument_checking,
                   attribute_checking = attribute_checking,
                   bound_methods = bound_methods,
                   descriptors = descriptors,
                   source_tracking = source_tracking,
                   line_tracking = line_tracking,
                   store_source = store_source,
                   inline_code = inline_code,
                   operator_funcs = operator_funcs,
                   number_classes = number_classes,
                  )
    output.close()
    return t.imported_modules, t.imported_js

def merge(ast, module_name, tree1, tree2, flags):
    if 'FULL_OVERRIDE' in flags:
        return tree2
    for child in tree2.node:
        if isinstance(child, ast.Function):
            replaceFunction(ast, module_name, tree1, child.name, child)
        elif isinstance(child, ast.Class):
            replaceClassMethods(ast, module_name, tree1, child.name, child)
        else:
            raise TranslationError(
                "Do not know how to merge %s" % child, child, module_name)
    return tree1

def replaceFunction(ast, module_name, tree, function_name, function_node):
    # find function to replace
    for child in tree.node:
        if isinstance(child, ast.Function) and child.name == function_name:
            copyFunction(child, function_node)
            return
    raise TranslationError(
        "function not found: " + function_name, function_node, module_name)

def copyFunction(target, source):
    target.code = source.code
    target.argnames = source.argnames
    target.defaults = source.defaults
    target.doc = source.doc # @@@ not sure we need to do this any more

def addCode(target, source):
    target.nodes.append(source)



def replaceClassMethods(ast, module_name, tree, class_name, class_node):
    # find class to replace
    old_class_node = None
    for child in tree.node:
        if isinstance(child, ast.Class) and child.name == class_name:
            old_class_node = child
            break

    if not old_class_node:
        raise TranslationError(
            "class not found: " + class_name, class_node, module_name)

    # replace methods
    for node in class_node.code:
        if isinstance(node, ast.Function):
            found = False
            for child in old_class_node.code:
                if isinstance(child, ast.Function) and child.name == node.name:
                    found = True
                    copyFunction(child, node)
                    break

            if not found:
                raise TranslationError(
                    "class method not found: " + class_name + "." + node.name,
                    node, module_name)
        elif isinstance(node, ast.Assign) and \
             isinstance(node.nodes[0], ast.AssName):
            found = False
            for child in old_class_node.code:
                if isinstance(child, ast.Assign) and \
                    eqNodes(child.nodes, node.nodes):
                    found = True
                    copyAssign(child, node)
            if not found:
                addCode(old_class_node.code, node)
        elif isinstance(node, ast.Pass):
            pass
        else:
            raise TranslationError(
                "Do not know how to merge %s" % node, node, self.module_name)



class PlatformParser:
    def __init__(self, compiler,
                       platform_dir = "", verbose=True, chain_plat=None):
        self.platform_dir = platform_dir
        self.parse_cache = {}
        self.platform = ""
        self.verbose = verbose
        self.chain_plat = chain_plat
        self.compiler = compiler

    def setPlatform(self, platform):
        self.platform = platform

    def parseModule(self, module_name, file_name):

        importing = False
        if not self.parse_cache.has_key(file_name):
            importing = True
            if self.chain_plat:
                mod, override = self.chain_plat.parseModule(module_name,
                                                            file_name)
            else:
                mod = self.compiler.parseFile(file_name)
            self.parse_cache[file_name] = mod
        else:
            mod = self.parse_cache[file_name]

        override = False
        platform_file_name = self.generatePlatformFilename(file_name)
        if self.platform and os.path.isfile(platform_file_name):
            mod = copy.deepcopy(mod)
            mod_override = self.compiler.parseFile(platform_file_name)
            if self.verbose:
                print "Merging", module_name, self.platform
            self.merge(smod, mod_override)
            override = True

        if self.verbose:
            if override:
                print "Importing %s (Platform %s)" % (module_name, self.platform)
            elif importing:
                print "Importing %s" % (module_name)

        return mod, override

    def generatePlatformFilename(self, file_name):
        (module_name, extension) = os.path.splitext(os.path.basename(file_name))
        platform_file_name = module_name + self.platform + extension

        return os.path.join(os.path.dirname(file_name), self.platform_dir, platform_file_name)

    def replaceFunction(self, tree, function_name, function_node):
        # find function to replace
        for child in tree.node:
            if isinstance(child, self.ast.Function) and child.name == function_name:
                self.copyFunction(child, function_node)
                return
        raise TranslationError(
            "function not found: " + function_name,
            function_node, self.module_name)

    def replaceClassMethods(self, tree, class_name, class_node):
        # find class to replace
        old_class_node = None
        for child in tree.node:
            if isinstance(child, self.ast.Class) and child.name == class_name:
                old_class_node = child
                break

        if not old_class_node:
            raise TranslationError(
                "class not found: " + class_name, class_node, self.module_name)

        # replace methods
        for node in class_node.code:
            if isinstance(node, self.ast.Function):
                found = False
                for child in old_class_node.code:
                    if isinstance(child, self.ast.Function) and child.name == node.name:
                        found = True
                        self.copyFunction(child, node)
                        break

                if not found:
                    raise TranslationError(
                        "class method not found: " + class_name + "." + node.name,
                        node, self.module_name)
            elif isinstance(node, self.ast.Assign) and \
                 isinstance(node.nodes[0], self.ast.AssName):
                found = False
                for child in old_class_node.code:
                    if isinstance(child, self.ast.Assign) and \
                        self.eqNodes(child.nodes, node.nodes):
                        found = True
                        self.copyAssign(child, node)
                if not found:
                    self.addCode(old_class_node.code, node)
            elif isinstance(node, self.ast.Pass):
                pass
            else:
                raise TranslationError(
                    "Do not know how to merge %s" % node,
                    node, self.module_name)

    def copyFunction(self, target, source):
        target.code = source.code
        target.argnames = source.argnames
        target.defaults = source.defaults
        target.doc = source.doc # @@@ not sure we need to do this any more

    def copyAssign(self, target, source):
        target.nodes = source.nodes
        target.expr = source.expr
        target.lineno = source.lineno
        return

    def eqNodes(self, nodes1, nodes2):
        return str(nodes1) == str(nodes2)

def dotreplace(fname):
    path, ext = os.path.splitext(fname)
    return path.replace(".", "/") + ext

class AppTranslator:

    def __init__(self, compiler,
                 library_dirs=[], parser=None, dynamic=False,
                 verbose=True,
                 debug=False,
                 print_statements=True,
                 function_argument_checking=True,
                 attribute_checking=True,
                 bound_methods=True,
                 descriptors=True,
                 source_tracking=True,
                 line_tracking=True,
                 store_source=True,
                 inline_code=False,
                 operator_funcs=True,
                 number_classes=True,
                ):
        self.compiler = compiler
        self.extension = ".py"
        self.print_statements = print_statements
        self.library_modules = []
        self.overrides = {}
        self.library_dirs = path + library_dirs
        self.dynamic = dynamic
        self.verbose = verbose
        self.debug = debug
        self.print_statements = print_statements
        self.function_argument_checking = function_argument_checking
        self.attribute_checking = attribute_checking
        self.bound_methods = bound_methods
        self.descriptors = descriptors
        self.source_tracking = source_tracking
        self.line_tracking = line_tracking
        self.store_source = store_source
        self.inline_code = inline_code
        self.operator_funcs = operator_funcs
        self.number_classes = number_classes

        if not parser:
            self.parser = PlatformParser(self.compiler)
        else:
            self.parser = parser

        self.parser.dynamic = dynamic

    def findFile(self, file_name):
        if os.path.isfile(file_name):
            return file_name

        for library_dir in self.library_dirs:
            file_name = dotreplace(file_name)
            full_file_name = os.path.join(
                    LIBRARY_PATH, library_dir, file_name)
            if os.path.isfile(full_file_name):
                return full_file_name

            fnameinit, ext = os.path.splitext(file_name)
            fnameinit = fnameinit + "/__init__.py"

            full_file_name = os.path.join(
                    LIBRARY_PATH, library_dir, fnameinit)
            if os.path.isfile(full_file_name):
                return full_file_name

        raise Exception("file not found: " + file_name)

    def _translate(self, module_name, debug=False):
        self.library_modules.append(module_name)
        file_name = self.findFile(module_name + self.extension)

        output = StringIO()

        f = file(file_name, "r")
        src = f.read()
        f.close()

        mod, override = self.parser.parseModule(module_name, file_name)
        if override:
            override_name = "%s.%s" % (self.parser.platform.lower(),
                                           module_name)
            self.overrides[override_name] = override_name
        t = Translator(self.compiler,
                       module_name, file_name, src, mod, output, 
                       self.dynamic, self.findFile, 
                       debug = self.debug,
                       print_statements = self.print_statements,
                       function_argument_checking = self.function_argument_checking,
                       attribute_checking = self.attribute_checking,
                       bound_methods = self.bound_methods,
                       descriptors = self.descriptors,
                       source_tracking = self.source_tracking,
                       line_tracking = self.line_tracking,
                       store_source = self.store_source,
                       inline_code = self.inline_code,
                       operator_funcs = self.operator_funcs,
                       number_classes = self.number_classes,
                      )

        module_str = output.getvalue()
        imported_modules_str = ""
        for module in t.imported_modules:
            if module not in self.library_modules:
                self.library_modules.append(module)

        return imported_modules_str + module_str


    def translate(self, module_name, is_app=True, debug=False,
                  library_modules=[]):
        app_code = StringIO()
        lib_code = StringIO()
        imported_js = []
        self.library_modules = []
        self.overrides = {}
        for library in library_modules:
            if library.endswith(".js"):
                imported_js.append(library)
                continue
            self.library_modules.append(library)
            if self.verbose:
                print 'Including LIB', library
            print >> lib_code, '\n//\n// BEGIN LIB '+library+'\n//\n'
            print >> lib_code, self._translate(
                library, False, debug=debug, imported_js=imported_js)

            print >> lib_code, "/* initialize static library */"
            print >> lib_code, "%s();\n" % library

            print >> lib_code, '\n//\n// END LIB '+library+'\n//\n'
        if module_name:
            print >> app_code, self._translate(
                module_name, is_app, debug=debug, imported_js=imported_js)
        for js in imported_js:
           path = self.findFile(js)
           if os.path.isfile(path):
              if self.verbose:
                  print 'Including JS', js
              print >> lib_code,  '\n//\n// BEGIN JS '+js+'\n//\n'
              print >> lib_code, file(path).read()
              print >> lib_code,  '\n//\n// END JS '+js+'\n//\n'
           else:
              print >>sys.stderr, 'Warning: Unable to find imported javascript:', js
        return lib_code.getvalue(), app_code.getvalue()

def add_compile_options(parser):
    global debug_options, speed_options, pythonic_options

    parser.add_option("--internal-ast",
                      dest="internal_ast",
                      action="store_true",
                      help="Use internal AST parser instead of standard python one"
                     )

    parser.add_option("--debug-wrap",
                      dest="debug",
                      action="store_true",
                      help="Wrap function calls with javascript debug code",
                     )
    parser.add_option("--no-debug-wrap",
                      dest="debug",
                      action="store_false",
                     )
    debug_options['debug'] = True
    speed_options['debug'] = False

    parser.add_option("--no-print-statements",
                      dest="print_statements",
                      action="store_false",
                      help="Remove all print statements",
                     )
    parser.add_option("--print-statements",
                      dest="print_statements",
                      action="store_true",
                      help="Generate code for print statements",
                     )
    speed_options['print_statements'] = False

    parser.add_option("--no-function-argument-checking",
                      dest = "function_argument_checking",
                      action="store_false",
                      help = "Do not generate code for function argument checking",
                     )
    parser.add_option("--function-argument-checking",
                      dest = "function_argument_checking",
                      action="store_true",
                      help = "Generate code for function argument checking",
                     )
    speed_options['function_argument_checking'] = False
    pythonic_options['function_argument_checking'] = True

    parser.add_option("--no-attribute-checking",
                      dest = "attribute_checking",
                      action="store_false",
                      help = "Do not generate code for attribute checking",
                     )
    parser.add_option("--attribute-checking",
                      dest = "attribute_checking",
                      action="store_true",
                      help = "Generate code for attribute checking",
                     )
    speed_options['attribute_checking'] = False
    pythonic_options['attribute_checking'] = True

    parser.add_option("--no-bound-methods",
                      dest = "bound_methods",
                      action="store_false",
                      help = "Do not generate code for binding methods",
                     )
    parser.add_option("--bound-methods",
                      dest = "bound_methods",
                      action="store_true",
                      help = "Generate code for binding methods",
                     )
    speed_options['bound_methods'] = False
    pythonic_options['bound_methods'] = True

    parser.add_option("--no-descriptors",
                      dest = "descriptors",
                      action="store_false",
                      help = "Do not generate code for descriptor calling",
                     )
    parser.add_option("--descriptors",
                      dest = "descriptors",
                      action="store_true",
                      help = "Generate code for descriptor calling",
                     )
    speed_options['descriptors'] = False
    pythonic_options['descriptors'] = True

    parser.add_option("--no-source-tracking",
                      dest = "source_tracking",
                      action="store_false",
                      help = "Do not generate code for source tracking",
                     )
    parser.add_option("--source-tracking",
                      dest = "source_tracking",
                      action="store_true",
                      help = "Generate code for source tracking",
                     )
    debug_options['source_tracking'] = True
    speed_options['source_tracking'] = False
    pythonic_options['source_tracking'] = True

    parser.add_option("--no-line-tracking",
                      dest = "line_tracking",
                      action="store_true",
                      help = "Do not generate code for source tracking on every line",
                     )
    parser.add_option("--line-tracking",
                      dest = "line_tracking",
                      action="store_true",
                      help = "Generate code for source tracking on every line",
                     )
    debug_options['line_tracking'] = True
    pythonic_options['line_tracking'] = True

    parser.add_option("--no-store-source",
                      dest = "store_source",
                      action="store_false",
                      help = "Do not store python code in javascript",
                     )
    parser.add_option("--store-source",
                      dest = "store_source",
                      action="store_true",
                      help = "Store python code in javascript",
                     )
    debug_options['store_source'] = True
    pythonic_options['store_source'] = True

    parser.add_option("--no-inline-code",
                      dest = "inline_code",
                      action="store_false",
                      help = "Do not generate inline code for bool/eq/len",
                     )
    parser.add_option("--inline-code",
                      dest = "inline_code",
                      action="store_true",
                      help = "Generate inline code for bool/eq/len",
                     )
    speed_options['inline_code'] = True

    parser.add_option("--no-operator-funcs",
                      dest = "operator_funcs",
                      action="store_false",
                      help = "Do not generate function calls for operators",
                     )
    parser.add_option("--operator-funcs",
                      dest = "operator_funcs",
                      action="store_true",
                      help = "Generate function calls for operators",
                     )
    speed_options['operator_funcs'] = False
    pythonic_options['operator_funcs'] = True

    parser.add_option("--no-number-classes",
                      dest = "number_classes",
                      action="store_false",
                      help = "Do not use number classes",
                     )
    parser.add_option("--number-classes",
                      dest = "number_classes",
                      action="store_true",
                      help = "Use classes for numbers (float, int, long)",
                     )
    speed_options['number_classes'] = False
    pythonic_options['number_classes'] = True


    def set_multiple(option, opt_str, value, parser, **kwargs):
        for k in kwargs.keys():
            setattr(parser.values, k, kwargs[k])

    parser.add_option("-d", "--debug",
                      action="callback",
                      callback = set_multiple,
                      callback_kwargs = debug_options,
                      help="Set all debugging options",
                     )
    parser.add_option("-O",
                      action="callback",
                      callback = set_multiple,
                      callback_kwargs = speed_options,
                      help="Set all options that maximize speed",
                     )
    parser.add_option("--strict",
                      action="callback",
                      callback = set_multiple,
                      callback_kwargs = pythonic_options,
                      help="Set all options that mimic standard python behavior",
                     )
    parser.set_defaults(debug=False,
                        print_statements=True,
                        function_argument_checking = False,
                        attribute_checking = False,
                        bound_methods = True,
                        descriptors = False,
                        source_tracking = False,
                        line_tracking = False,
                        store_source = False,
                        inline_code = False,
                        operator_funcs = True,
                        number_classes = False,
                       )


usage = """
  usage: %prog [options] file...
"""

def main():
    import sys
    from optparse import OptionParser

    parser = OptionParser(usage = usage)
    parser.add_option("-o", "--output", dest="output",
                      help="Place the output into <output>")
    parser.add_option("-m", "--module-name", dest="module_name",
                      help="Module name of output")
    add_compile_options(parser)
    (options, args) = parser.parse_args()

    if len(args)<1:
        parser.error("incorrect number of arguments")

    compiler = import_compiler(options.internal_ast)

    if not options.output:
        parser.error("No output file specified")
    options.output = os.path.abspath(options.output)

    file_names = map(os.path.abspath, args)
    for fn in file_names:
        if not os.path.isfile(fn):
            print >> sys.stderr, "Input file not found %s" % fn
            sys.exit(1)

    translate(compiler, file_names, options.output, options.module_name,
              debug = options.debug,
              print_statements = options.print_statements,
              function_argument_checking = options.function_argument_checking,
              attribute_checking = options.attribute_checking,
              bound_methods = options.bound_methods,
              source_tracking = options.source_tracking,
              line_tracking = options.line_tracking,
              store_source = options.store_source,
              inline_code = options.inline_code,
              operator_funcs = options.operator_funcs,
              number_classes = options.number_classes,
    ),

if __name__ == "__main__":
    main()

