import os
import sys
import traceback

test_pyjs = True
test_std = True

from astpprint import getAststr, printAst

if test_pyjs:
    from lib2to3 import compiler as test_compiler
    from lib2to3.compiler.transformer import Transformer
    from lib2to3.compiler import parser as test_parser

#g = Grammar()

if test_std:
    import compiler
    import parser

def compare_compilers(fname):

    path, fname_out = os.path.split(fname)

    f = open(fname)
    txt = f.read()
    f.close()

    if test_std:
        try:
            x1 = compiler.parseFile(fname)
            ys1 = getAststr(compiler.ast, x1)
        except SyntaxError:
            ys1 = traceback.format_exc(limit=0)
            
    if test_pyjs:
        try:
            y = test_compiler.parseFile(fname)
            ys = getAststr(test_compiler.ast, y)

        except SyntaxError:
            ys = traceback.format_exc(limit=1)

    if not test_pyjs and not test_std:
        return

    if ys == ys1:
        print "passed"
        return

    print "failed."

    if test_pyjs:
        f = open(fname_out+".ast", "w")
        f.write(ys)
        f.close()

    if test_std:
        f = open(fname_out+".ast.std", "w")
        f.write(ys1)
        f.close()

import sys
for arg in sys.argv[1:]:
    print "test file", arg
    try:
        compare_compilers(arg)
    except:
        print >> sys.stderr, "exception in compile of ", arg
        traceback.print_exc()
        sys.stderr.flush()

