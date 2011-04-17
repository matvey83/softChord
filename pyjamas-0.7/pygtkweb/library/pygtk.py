version = '2.0'

def require(ver):
    if float(version) > float(ver):
        raise Exception("required version % not found" % ver)
