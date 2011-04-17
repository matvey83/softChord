# pyv8_print_fn is actually in pyv8run.py and is added to the Globals
def printFunc(objs, newline):
    JS("""
        var s = "";
        for(var i=0; i < objs.length; i++) {
            if(s != "") s += " ";
                s += objs[i];
        }

        pyv8_print_fn(s);
    """)

def __dynamic_load__(importName):
    setCompilerOptions("noDebug")
    module = JS("""$pyjs.loaded_modules[importName]""")
    if JS("""typeof module == 'undefined'"""):
        try:
            dynamic.ajax_import("lib/" + importName + ".__" + platform + "__.js")
            module = JS("""$pyjs.loaded_modules[importName]""")
        except:
            pass
    if JS("""typeof module == 'undefined'"""):
        try:
            dynamic.ajax_import("lib/" + importName + ".js")
            module = JS("""$pyjs.loaded_modules[importName]""")
        except:
            pass
    #if JS("""typeof module == 'undefined'"""):
    #    module = pyv8_import_module(None, importName)
    return module

def debugReport(msg):
    JS("""
    pyv8_print_fn(msg);
    """)

def open(fname, mode='r'):
    return JS("pyv8_open(fname, mode);")


