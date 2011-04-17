
def printFunc(objs, newline):
    JS("""
    print.apply(this, objs);
    """)

def debugReport(msg):
    JS("""
    print(msg);
    """)

