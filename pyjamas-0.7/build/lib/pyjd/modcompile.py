#!/usr/bin/env python
# Copyright 2006 James Tauber and contributors
# Copyright (C) 2009, Luke Kenneth Casson Leighton <lkcl@lkcl.net>
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
import compiler
from compiler import ast, syntax
from compiler import misc # good grief, this doesn't look good
import os
import copy
import imp

from compiler.pycodegen import ModuleCodeGenerator

class PlatformParser:
    def __init__(self, platform_dir = "", verbose=True, chain_plat=None):
        self.platform_dir = platform_dir
        self.parse_cache = {}
        self.platform = ""
        self.verbose = verbose
        self.chain_plat = chain_plat

    def setPlatform(self, platform):
        self.platform = platform

    def parseModule(self, module_name, file_name):

        importing = False
        if not self.parse_cache.has_key(file_name):
            importing = True
            if self.chain_plat:
                mod, _ov = self.chain_plat.parseModule(module_name, file_name)
            else:
                mod = compiler.parseFile(file_name)
            self.parse_cache[file_name] = mod
        else:
            mod = self.parse_cache[file_name]

        override = False
        platform_file_name = self.generatePlatformFilename(file_name)
        print "platform", platform_file_name
        if self.platform and os.path.isfile(platform_file_name):
            mod = copy.deepcopy(mod)
            mod_override = compiler.parseFile(platform_file_name)
            if self.verbose:
                print "Merging", module_name, self.platform
            merge(module_name, mod, mod_override)
            override = True

        if self.verbose:
            if override:
                print "Importing %s (Platform %s)" % (module_name, self.platform)
            elif importing:
                print "Importing %s" % (module_name)

        if override:
            return mod, platform_file_name
        return mod, file_name

    def generatePlatformFilename(self, file_name):
        (module_name, extension) = os.path.splitext(os.path.basename(file_name))
        platform_file_name = module_name + self.platform + extension

        return os.path.join(os.path.dirname(file_name), self.platform_dir, platform_file_name)

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
        self.message = "%s line %s:\n%s\n%s" % (module_name, lineno, msg, node)

    def __str__(self):
        return self.message

def merge(module_name, tree1, tree2):
    for child in tree2.node:
        if isinstance(child, ast.Function):
            replaceFunction(tree1, child.name, child)
        elif isinstance(child, ast.Class):
            replaceClassMethods(tree1, child.name, child)
        else:
            raise TranslationError(
                "Do not know how to merge %s" % child, child, module_name)
    return tree1

def replaceFunction(tree, function_name, function_node):
    # find function to replace
    for child in tree.node:
        if isinstance(child, ast.Function) and child.name == function_name:
            copyFunction(child, function_node)
            return
    raise TranslationError(
        "function not found: " + function_name, function_node, None)

def copyFunction(target, source):
    target.code = source.code
    target.argnames = source.argnames
    target.defaults = source.defaults
    target.doc = source.doc # @@@ not sure we need to do this any more

def addCode(target, source):
    target.nodes.append(source)

def copyAssign(target, source):
    target.nodes = source.nodes
    target.expr = source.expr
    target.lineno = source.lineno

def eqNodes(nodes1, nodes2):
        return str(nodes1) == str(nodes2)

def replaceClassMethods(tree, class_name, class_node):
    # find class to replace
    old_class_node = None
    for child in tree.node:
        if isinstance(child, ast.Class) and child.name == class_name:
            old_class_node = child
            break

    if not old_class_node:
        raise TranslationError(
            "class not found: " + class_name, class_node, self.module_name)

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
                    node, self.module_name)
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

class Module:

    mode = "exec"

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename
        self.code = None

    def _get_tree(self):
        misc.set_filename(self.filename, self.tree)
        syntax.check(self.tree)
        return self.tree

    def compile(self):
        pass # implemented by subclass

    def getCode(self):
        return self.code

    def compile(self, display=0):
        tree = self._get_tree()
        gen = ModuleCodeGenerator(tree)
        if display:
            import pprint
            print pprint.pprint(tree)
        self.code = gen.getCode()

    def dump(self, f):
        f.write(self.getPycHeader())
        marshal.dump(self.code, f)

    MAGIC = imp.get_magic()

    def getPycHeader(self):
        # compile.c uses marshal to write a long directly, with
        # calling the interface that would also generate a 1-byte code
        # to indicate the type of the value.  simplest way to get the
        # same effect is to call marshal and then skip the code.
        mtime = os.path.getmtime(self.filename)
        mtime = struct.pack('<i', mtime)
        return self.MAGIC + mtime

