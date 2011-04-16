
"""
Usage:

epydoc [--html|--pdf] [-o DIR] [--parse-only|--introspect-only] [-v|-q]
       [--name NAME] [--url URL] [--docformat NAME] [--graph GRAPHTYPE]
       [--inheritance STYLE] [--config FILE] OBJECTS...
OBJECTS...
A list of the Python objects that should be documented. Objects can be specified using dotted names (such as os.path), module filenames (such as epydoc/epytext.py), or package directory names (such as epydoc/). Packages are expanded to include all sub-modules and sub-packages.

--html    Generate HTML output. (default)
--pdf    Generate Adobe Acrobat (PDF) output, using LaTeX.
-o DIR, --output DIR, --target DIR
     The output directory.
--parse-only, --introspect-only
     By default, epydoc will gather information about each Python object using two methods: parsing the object's source code; and importing the object and directly introspecting it. Epydoc combines the information obtained from these two methods to provide more complete and accurate documentation. However, if you wish, you can tell epydoc to use only one or the other of these methods. For example, if you are running epydoc on untrusted code, you should use the --parse-only option.
-v, -q    Increase (-v) or decrease (-q) the verbosity of the output. These options may be repeated to further increase or decrease verbosity. Docstring markup warnings are supressed unless -v is used at least once.
--name NAME    The documented project's name.
--url URL    The documented project's URL.
--docformat NAME
     The markup language that should be used by default to process modules' docstrings. This is only used for modules that do not define the special __docformat__ variable; it is recommended that you explicitly specify __docformat__ in all your modules.
--graph GRAPHTYPE
     
Include graphs of type GRAPHTYPE in the generated output. Graphs are generated using the Graphviz dot executable. If this executable is not on the path, then use --dotpath to specify its location. This option may be repeated to include multiple graph types in the output. To include all graphs, use --graph all. The available graph types are:
classtree: displays each class's base classes and subclasses;
callgraph: displays the callers and callees of each function or method. These graphs are based on profiling information, which must be specified using the --pstate option.
umlclass: displays each class's base classes and subclasses, using UML style. Methods and attributes are listed in the classes where they are defined. If type information is available about attributes (via the @type field), then those types are displayed as separate classes, and the attributes are displayed as associations.
--inheritance STYLE
     
The format that should be used to display inherited methods, variables, and properties. Currently, three styles are supported. To see an example of each style, click on it:
grouped: Inherited objects are gathered into groups, based on which class they are inherited from.
listed: Inherited objects are listed in a short list at the end of the summary table.
included: Inherited objects are mixed in with non-inherited objects.
--config FILE    Read the given configuration file, which can contain both options and Python object names. This option may be used multiple times, if you wish to use multiple configuration files. See Configuration Files for more information.
"""

import glob
from os.path import abspath, pathsep
import os
paths = glob.glob(abspath('../library/pyjamas/*.py')) + \
        glob.glob(abspath('../library/pyjamas/ui/*.py')) + \
        glob.glob(abspath('../library/pyjamas/Canvas/*.py')) + \
        glob.glob(abspath('../bin/*.py'))
print paths
command = ['epydoc', "-v",  "-v",
           '--parse-only',
           '--html',
           '-o', 'api', 
           '--name', 'Pyjamas', 
           '--url', 'http://pyjs.org', 
           ]+list(paths)

def quote_shell(x):
    if x.find(" ") != -1:
        return '"'+x+'"'
    return x
commandString = ' '.join(map(quote_shell, command))
from os import system
print '>>', commandString
system(commandString)
