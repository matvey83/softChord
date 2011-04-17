from lib2to3.pgen2.driver import load_grammar
from lib2to3.pgen2.driver import Driver
import os

gpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Grammar.txt")
g = load_grammar(gpath)

def suite(text):
    d = Driver(g )
    return d.parse_string(text)

# dummy
def st2tuple(tree, line_info=1):
    return tree
    
