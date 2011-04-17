import translator
import os
import sys
import util
import logging
import pyjs


if pyjs.pyjspth is None:
    PYLIB_PATH = os.path.join(os.path.dirname(__file__), 'lib')
    BUILTIN_PATH = os.path.join(os.path.dirname(__file__), 'builtin')
    PYJAMASLIB_PATH = os.path.split(os.path.dirname(__file__))[0]
    PYJAMASLIB_PATH = os.path.split(PYJAMASLIB_PATH)[0]
    PYJAMASLIB_PATH = os.path.join(os.path.split(PYJAMASLIB_PATH)[0], 'library')
else:
    PYLIB_PATH = os.path.join(pyjs.pyjspth, "pyjs", "src", "pyjs", "lib")
    BUILTIN_PATH = os.path.join(pyjs.pyjspth, "pyjs", "src", "pyjs", "builtin")
    PYJAMASLIB_PATH = os.path.join(pyjs.pyjspth, "library")

_path_cache= {}
def module_path(name, path):
    global _path_cache
    candidates = []
    packages = {}
    modules = {}
    if name.endswith('.js'):
        parts = [name]
    else:
        parts = name.split('.')
    if not name in _path_cache:
        _path_cache[name] = {}
    for p in path:
        if p in _path_cache[name]:
            if _path_cache[name][p] is None:
                continue
            return _path_cache[name][p]
        tail = []
        for pn in parts:
            tail.append(pn)
            mn = '.'.join(tail)
            cp = os.path.join(*([p] + tail))
            if mn in _path_cache:
                cache = _path_cache[mn]
            else:
                cache = {}
                _path_cache[mn] = cache
            if p in cache:
                if cache[p] is None:
                    break
            elif os.path.isdir(cp) and os.path.exists(
                os.path.join(cp, '__init__.py')):
                cache[p] = os.path.join(cp, '__init__.py')
            elif os.path.exists(cp + '.py'):
                cache[p] = cp + '.py'
            elif pn.endswith('.js') and os.path.exists(cp):
                cache[p] = cp
            else:
                cache[p] = None
        if p in _path_cache[name] and not _path_cache[name][p] is None:
            return _path_cache[name][p]
        _path_cache[name][p] = None
    
    return None
    raise RuntimeError, "Module %r not found" % name


class BaseLinker(object):

    platform_parents = {}

    def __init__(self, modules, output='output',
                 compiler=None,
                 debug=False, 
                 js_libs=[], static_js_libs=[], early_static_js_libs=[], late_static_js_libs=[], dynamic_js_libs=[],
                 early_static_app_libs = [], unlinked_modules = [], keep_lib_files = False,
                 platforms=[], path=[],
                 translator_arguments={},
                 compile_inplace=False):
        modules = [mod.replace(os.sep, '.') for mod in modules]
        self.compiler = compiler
        self.js_path = os.path.abspath(output)
        self.top_module = modules[0]
        self.modules = modules
        self.output = os.path.abspath(output)
        self.js_libs = list(js_libs)
        self.static_js_libs = list(static_js_libs)
        self.early_static_js_libs = list(early_static_js_libs)
        self.late_static_js_libs = list(late_static_js_libs)
        self.dynamic_js_libs = list(dynamic_js_libs)
        self.early_static_app_libs = list(early_static_app_libs)
        self.unlinked_modules = unlinked_modules
        self.keep_lib_files = keep_lib_files
        self.platforms = platforms
        self.path = path + [PYLIB_PATH]
        self.translator_arguments = translator_arguments
        self.compile_inplace = compile_inplace
        self.top_module_path = None
        self.remove_files = {}

    def __call__(self):
        try:
            self.visited_modules = {}
            self.done = {}
            self.dependencies = {}
            self.visit_start()
            for platform in [None] + self.platforms:
                self.visit_start_platform(platform)
                old_path = self.path
                self.path = [BUILTIN_PATH, PYLIB_PATH, PYJAMASLIB_PATH]
                self.visit_modules(['pyjslib'], platform)
                self.path = old_path
                self.visit_modules(self.modules, platform)
                self.visit_end_platform(platform)
            self.visit_end()
        except translator.TranslationError, e:
            raise e

    def visit_modules(self, module_names, platform=None, parent_file = None):
        prefix = ''
        all_names = []
        for mn in module_names:
            if not mn.endswith(".js"):
                prefix = ''
                for part in mn.split('.')[:-1]:
                    pn = prefix + part
                    prefix = pn + '.'
                    if pn not in all_names:
                        all_names.append(pn)
            all_names.append(mn)
        paths = self.path
        parent_base = None
        abs_name = None
        if not parent_file is None:
            for p in paths:
                if parent_file.find(p) == 0 and p != parent_file:
                    parent_base = p
                    abs_name = os.path.split(parent_file)[0]
                    abs_name = '.'.join(abs_name[len(parent_base)+1:].split(os.sep))

        for mn in all_names:
            p = None
            if abs_name:
                p = module_path(abs_name + '.' + mn, [parent_base])
                if p:
                    mn = abs_name + '.' + mn
            if not p:
                p = module_path(mn, paths)
            if not p:
                continue
                raise RuntimeError, "Module %r not found. Dep of %r" % (
                    mn, self.dependencies)
            if mn==self.top_module:
                self.top_module_path = p
            override_paths=[]
            if platform:
                for pl in self.platform_parents.get(platform, []) + [platform]:
                    override_path = module_path('__%s__.%s' % (pl, mn),
                                                paths)
                    # prevent package overrides
                    if override_path and not override_path.endswith('__init__.py'):
                        override_paths.append(override_path)
            self.visit_module(p, override_paths, platform, module_name=mn)

    def visit_module(self, file_path, overrides, platform,
                     module_name):
        dir_name, file_name = os.path.split(file_path)
        if (     not file_name.endswith('.js')
             and file_name.split('.')[0] != module_name.split('.')[-1]
           ):
            if file_name == "__init__.py":
                if os.path.basename(dir_name) != module_name.split('.')[-1]:
                    return
            else:
                return
        self.merge_resources(dir_name)
        if platform and overrides:
            plat_suffix = '.__%s__' % platform
        else:
            plat_suffix = ''
        if self.compile_inplace:
            mod_part, extension = os.path.splitext(file_path)
            out_file = '%s%s.js' % (mod_part, plat_suffix)
        else:
            out_file = os.path.join(self.output, 'lib',
                                    '%s%s.js' % (module_name, plat_suffix))
        if out_file in self.done.get(platform, []):
            return
        
        # translate if
        #  -    no platform
        #  - or if we have an override
        #  - or the module is used in an override only
        if (   platform is None
            or (platform and overrides)
            or (out_file not in self.done.get(None,[]))
           ):
            if file_name.endswith('.js'):
                fp = open(out_file, 'w')
                fp.write("/* start javascript include: %s */\n" % file_name)
                fp.write(open(file_path, 'r').read())
                fp.write("$pyjs.loaded_modules['%s'] = function ( ) {return null;};\n" % file_name)
                fp.write("/* end %s */\n" % file_name)
                deps = []
                self.dependencies[out_file] = deps
            else:
                logging.info('Translating module:%s platform:%s out:%r' % (
                    module_name, platform or '-', out_file))
                deps, js_libs = translator.translate(self.compiler,
                                            [file_path] +  overrides,
                                            out_file,
                                            module_name=module_name,
                                            **self.translator_arguments)
                self.dependencies[out_file] = deps
                for path, mode, location in js_libs:
                    if mode == 'default':
                        if self.multi_file:
                            mode = 'dynamic'
                        else:
                            mode = 'static'
                    if mode == 'dynamic':
                        self.dynamic_js_libs.append(path)
                    elif mode == 'static':
                        if location == 'early':
                            self.early_static_js_libs.append(path)
                        elif location == 'middle':
                            self.static_js_libs.append(path)
                        elif location == 'late':
                            self.late_static_js_libs.append(path)
                        else:
                            raise RuntimeError, "Unknown js lib location: %r" % location
                    else:
                        raise RuntimeError, "Unknown js lib mode: %r" % mode

                if '.' in module_name:
                    for i, dep in enumerate(deps):
                        if module_path(dep, path=[dir_name]):
                            deps[i] = '.'.join(module_name.split('.')[:-1] + [dep])
        else:
            deps = self.dependencies[out_file]
        if out_file not in self.done.setdefault(platform, []):
            self.done[platform].append(out_file)
        if module_name not in self.visited_modules.setdefault(platform, []):
            self.visited_modules[platform].append(module_name)
        if deps:
            self.visit_modules(deps, platform, file_path)

    def merge_resources(self, dir_name):
        """gets a directory path for each module visited, this can be
        used to collect resources e.g. public folders"""
        pass

    def visit_start(self):
        if not os.path.exists(self.output):
            os.mkdir(self.output)
        if not self.compile_inplace:
            lib_dir = os.path.join(self.output, 'lib')
            if not os.path.exists(lib_dir):
                os.mkdir(lib_dir)

    def visit_start_platform(self, platform):
        pass

    def visit_end_platform(self, platform):
        pass

    def visit_end(self):
        pass


def add_linker_options(parser):
    parser.add_option("-o", "--output", dest="output", default='output',
                      help="directory to which the app should be written")

    parser.add_option("-j", "--include-js", dest="js_includes",
                      action="append", default=[],
                      help="javascripts to load into the same frame as the rest of the script")
    parser.add_option("-I", "--library_dir", dest="library_dirs",
                      default=[],
                      action="append", help="additional paths appended to PYJSPATH")

