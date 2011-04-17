"""Python AST pretty-printer.

Copyright(C) 2007, Martin Blais <blais@furius.ca>

This module exports a function that can be used to print a human-readable
version of the AST.

This code is downloaded verbatim from:
    http://code.activestate.com/recipes/533146/

"""
__author__ = 'Martin Blais <blais@furius.ca>'

import sys

__all__ = ('printAst','getAststr')

from StringIO import StringIO

def getAststr(astmod, ast, indent='  ', initlevel=0):
    "Pretty-print an AST to the given output stream."
    stream = StringIO()
    rec_node(astmod, ast, initlevel, indent, stream.write)
    stream.write('\n')
    stream.seek(0)
    return stream.read()

def printAst(astmod, ast, indent='  ', stream=sys.stdout, initlevel=0):
    "Pretty-print an AST to the given output stream."
    rec_node(astmod, ast, initlevel, indent, stream.write)
    stream.write('\n')
    stream.flush()

def rec_node(astmod, node, level, indent, write):
    "Recurse through a node, pretty-printing it."
    pfx = indent * level
    if isinstance(node, astmod.Node):
        write(pfx)
        write(node.__class__.__name__)
        write('(')

        i = 0
        for child in node.getChildren():
            if not isinstance(child, astmod.Node):
                continue
            if i != 0:
                write(',')
            write('\n')
            rec_node(astmod, child, level+1, indent, write)
            i += 1
        if i == 0:
            # None of the children as nodes, simply join their repr on a single
            # line.
            res = []
            for child in node.getChildren():
                res.append(repr(child))
            write(', '.join(res))
        else:
            write('\n')
            write(pfx)

        write(')')

    else:
        write(pfx)
        write(repr(node))


def main():
    from compiler import ast
    import optparse
    parser = optparse.OptionParser(__doc__.strip())
    opts, args = parser.parse_args()

    if not args:
        parser.error("You need to specify the name of Python files to print out.")

    import compiler, traceback
    for fn in args:
        print '\n\n%s:\n' % fn
        try:
            printAst(ast, compiler.parseFile(fn), initlevel=1)
        except SyntaxError, e:
            traceback.print_exc()

if __name__ == '__main__':
    main()


