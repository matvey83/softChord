class NF:
    def __init__(self, fmt):
        self.fmt = fmt

    def format(self, num):
        """ cheerfully ignore the number format requested
            and just return the number converted to a string
        """
        return str(num)

def getFormat(fmt):
    return NF(fmt)

