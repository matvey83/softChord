raise RuntimeError, "this module is deprecated, use the one in library"

def decodeURI(s):    
    """
    Built-in javascript function to decode a URI
    """
    
def decodeURIComponent(s):
    """
    Built-in javascript function to decode a URI component
    """

def encodeURI(s):
    """
    Built-in javascript function to encode a URI
    
    >> encodeURI(",/?:@&=+$# ")
    ",/?:@&=+$#%20"
    """

def encodeURIComponent(s):
    """
    Built-in javascript function to encode a URI component
    
    >>> encodeURIComponent(",/?:@&=+$# ")
    "%2C%2F%3F%3A%40%26%3D%2B%24%23%20"
    """

def escape(s):
    """
    Built-in javascript function to HTML escape a string.
    
    The escape() function encodes special characters, with the exception of:
        * @ - _ + . /
    
    Use the unescape() function to decode strings encoded with escape().
    
    For example:
    
    >>> escape("?!=()#%&")
    %3F%21%3D%28%29%23%25%26
    
    """

def unescape(s):
    """
    Use the unescape() function to decode strings encoded with escape().

    """
    
def JS(code):
    """
        Outputs the given javascript code as-is into the generated
        javascript code.
    """


class console:
    """
        Firebug console object stub.
    """
    
    @staticmethod
    def log(x, *args):
        """Print to the console"""

    @staticmethod
    def error(x, *args):
        """Print to the console"""

     
