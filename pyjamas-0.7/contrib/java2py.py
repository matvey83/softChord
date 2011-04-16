#!/usr/bin/env python
""" Use this to help speed up manual conversion of e.g. GWT Java to e.g.
    Pyjamas python

    TODO: in java2pythonlinebyline and redofunctions, identify a list
    of variables and functions, and do replace "variable" with "self.variable"
"""

import sys
import string

def import_gwt_to_pyjamas(txt):
    """ this bit is specifically hard-coded to deal with gwt-dnd
        conversion.  almost everything else is "generic" java-to-python
    """
    if txt.startswith("package "):
        return ''
    if not txt.startswith('import '):
        return txt
    if txt == 'import com.google.gwt.dom.client.NativeEvent;':
        return 'from pyjamas.ui import Event'
    if txt.startswith('import com.google.gwt.user.client.ui.'):
        module = txt[37:-1]
        return "from pyjamas.ui.%s import %s" % (module, module)
    if txt.startswith('import com.google.gwt.user.client.'):
        module = txt[34:-1]
        if module == 'Element':
            return ''
        return "from pyjamas import %s" % module
    if txt.startswith('import com.allen_sauer.gwt.dnd.client.drop.'):
        module = txt[43:-1]
        return "from pyjamas.dnd.drop import %s" % module
    if txt.startswith('import com.allen_sauer.gwt.dnd.client.util.'):
        module = txt[43:-1]
        return "from pyjamas.dnd.util import %s" % module
    if txt.startswith('import com.googlecode.gchart.client.'):
        module = txt[36:-1]
        if module == 'GChart':
            return "from pyjamas.chart.GChart import GChart"
        return "from pyjamas.chart import %s" % module

    if txt.startswith('import com.allen_sauer.gwt.dnd.client.'):
        module = txt[38:-1]
        return "from pyjamas.dnd import %s" % module
    return ''

def convert_stupid_js_import_to_stupid_js_import(txt):
    """ this is GWT-to-PyJS-specific conversion: support of assembly-like
        direct insertion of javascript.  again, it's one of the few bits
        of non-generic java-to-python
    """
    txt = txt.replace("/*-{", '{\nJS("""')
    txt = txt.replace("}-*/", '""")\n}')
    return txt

def join_single_open_brace_to_previous_line(txt):
    res = []
    for l in txt.split("\n"):
        x = l.strip()
        if x == '{':
            res[-1] += (' {')
        else:
            res.append(l)
    return '\n'.join(res)

def countspaces(txt):
    count = 0
    while count < len(txt) and txt[count] == ' ':
        count += 1
    return count

def java2pythonlinebyline(txt):
    if txt.find('if (') >= 0:
        if not txt.strip().endswith("{"):
            print txt
            error # deliberate error on lines with no {
        txt = txt.replace('if (', 'if ')
        txt = txt.replace('!', 'not ')
        txt = txt.replace('not =', '!=') # whoops
        txt = txt.replace(') {', ':')
    elif txt.endswith("else {"):
        txt = txt.replace('else {', 'else:')
    elif txt.find('class ') >= 0 and txt.endswith("{"):
        txt = txt.replace('{', ':')
    elif txt.find('try {') >= 0:
        txt = txt.replace('try {', 'try:')
    elif txt.find('} catch') >= 0:
        txt = txt.replace('} catch', 'except')
    elif txt.find('finally {') >= 0:
        txt = txt.replace('finally {', 'except:')
    elif txt.find('while (') >= 0:
        txt = txt.replace('while (', 'while ')
        txt = txt.replace(') {', ':')
    elif txt.find('for (') >= 0:
        txt = txt.replace('for (', 'for ')
        txt = txt.replace(') {', ':')
    count = countspaces(txt)
    if txt[count:].startswith("}"):
        txt = count * ' ' + txt[count+1:]

    if txt[count:].startswith("protected ") >= 0:
        # TODO: check if "class" in current line, add class name
        # otherwise assume last word of line is variable
        txt = txt.replace("protected ", "")
    if txt[count:].startswith("public ") >= 0:
        # TODO: check if "class" in current line, add class name
        # otherwise assume last word of line is variable
        txt = txt.replace("public ", "")
    if txt[count:].startswith("private ") >= 0:
        # TODO: check if "class" in current line, add class name
        # otherwise assume last word of line is variable e.g.
        # private final Area >>>targetArea<<<;
        txt = txt.replace("private ", "")
    if txt[count:].startswith("static ") >= 0:
        txt = txt.replace("static ", "")
    if txt[count:].startswith("native ") >= 0:
        txt = txt.replace("native ", "")
    if txt[count:].startswith("final ") >= 0:
        txt = txt.replace("final ", "")
    if txt.endswith(";"):
        txt = txt[:-1]
    if txt.endswith(" :"):
        txt = txt[:-2] + ":"

    return txt

def redofunctions(txt):
    if txt.strip().startswith("#"):
        return txt
    if not txt.endswith("{"):
        return txt
    lbr = txt.find("(")
    rbr = txt.find(") {")
    if lbr == -1 or rbr == -1 or lbr > rbr:
        return txt
    lbr2 = txt.find("(", lbr+1)
    if lbr2 > 0:
        return txt
    count = countspaces(txt)
    pre = txt[count:lbr]
    args = txt[lbr+1:rbr]

    if pre.strip() == 'switch':
        return txt

    is_exception = 0
    if pre.find("except") >= 0:
        is_exception = 1
    else:
        pre = map(string.strip, pre.split(' '))
        if len(pre) == 1: # assume it's a constructor
            pre = '__init__'
        elif len(pre) == 2:
            pre = pre[-1] # drop the first word (return type)
        else:
            print txt, pre
            error # deliberately cause error - investigate 3-word thingies!

    args = map(string.strip, args.split(','))
    newargs = []
    for arg in args:
        if arg == '':
            continue
        arg = map(string.strip, arg.split(' '))
        if len(arg) == 2:
            newargs.append(arg[1]) # drop first word (arg type)
        else:
            print txt
            print pre, args, arg
            error # deliberately cause error - find out why arg no type
    if count != 0 and not is_exception:
        # assume class not global function - add self
        newargs = ['self'] + newargs
    newargs = ', '.join(newargs)
    if is_exception:
        return "%s%s%s:" % (count*' ', pre, newargs)
    return "%sdef %s(%s):" % (count*' ', pre, newargs)

def reindent(txt):
    """ reindents according to { and } braces.  strips all whitespace,
        possibly not smartest thing to do.  oh well.
    """
    res = ''
    indent = 0
    for l in txt.split("\n"):
        l = l.strip()
        if l.startswith("}"):
            indent -= 1
            if indent < 0:
                res += "INDENT ERROR"
        res += '    ' * indent + l + "\n"
        if l.endswith("{"):
            indent += 1
    return res

def java_replace(txt, rep, repwith):
    res = ''
    while txt:
        i = txt.find('JS("""')
        if i == -1:
            return res + txt.replace(rep, repwith)
        j = txt.find('""")', i)
        if (j == -1):
            error # whoops
        res += txt[:i].replace(rep, repwith) + txt[i:j]
        txt = txt[j:]
    return txt

def java_linemap(fn, lines):

    res = []
    in_stupid_js = False

    for l in lines:

        if in_stupid_js:
            res.append(l)
            if l.find('""")') >= 0:
                in_stupid_js = False
            continue

        if l.find('JS("""') >= 0:
            in_stupid_js = True
            res.append(l)
            continue
    
        res.append(fn(l))

    return res

def java2python(txt):
    txt = txt.replace("\r\n", '\n') # yuk dos files.
    txt = convert_stupid_js_import_to_stupid_js_import(txt)
    txt = join_single_open_brace_to_previous_line(txt)
    txt = reindent(txt)
    txt = java_replace(txt, "/*", '"""')
    txt = java_replace(txt, "*/", '"""')
    txt = java_replace(txt, "<>", '!=')
    txt = java_replace(txt, "&&", ' and ')
    txt = java_replace(txt, "||", ' or ')
    txt = java_replace(txt, "null", 'None')
    txt = java_replace(txt, "!= None", 'is not None')
    txt = java_replace(txt, "== None", 'is None')
    txt = java_replace(txt, "throw ", 'raise ')
    txt = java_replace(txt, "true", 'True')
    txt = java_replace(txt, "false", 'False')
    txt = java_replace(txt, "//", '#')
    txt = java_replace(txt, "this.", 'self.')
    txt = java_replace(txt, "else if", 'elif')
    txt = java_replace(txt, "new ", '')
    l = txt.split("\n")
    l = java_linemap(import_gwt_to_pyjamas, l)
    l = java_linemap(java2pythonlinebyline, l)
    l = java_linemap(redofunctions, l)
    txt = java_replace(txt, "}", '')
    return '\n'.join(l)

if __name__ == "__main__":
    fname = sys.argv[1]
    f = open(fname + ".java", "r")
    txt = java2python(f.read())
    f.close()

    f = open(fname + ".py", "w")
    f.write(txt)
    f.close()

