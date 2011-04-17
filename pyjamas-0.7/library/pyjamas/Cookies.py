# This is the gtk-dependent Cookies module.
# For the pyjamas/javascript version, see platform/CookiesPyJS.py

import sys
from __pyjamas__ import JS, doc
if sys.platform not in ['mozilla', 'ie6', 'opera', 'oldmoz', 'safari']:
    from Cookie import SimpleCookie
    import urllib
    import datetime
    from string import strip

def getCookie(key):
    return getCookie2(key)

def getCookie2(cookie_name):
    cookiestr = doc().cookie
    c = SimpleCookie(cookiestr)
    cs = c.get(cookie_name, None)
    print "getCookie2", cookiestr, "name", cookie_name, "val", cs
    if cs:
        return cs.value
    return None
    
# expires can be int or Date
def setCookie(name, value, expires, domain=None, path=None, secure=False):
    cookiestr = doc().cookie
    c = SimpleCookie(cookiestr)
    c[name] = value
    m = c[name]
    d = datetime.datetime.now() + datetime.timedelta(0, expires/1000)
    d = d.strftime("%a, %d %b %Y %H:%M:%S GMT")
    m['expires'] = '"%s"' % d
    if domain:
        m['domain'] = domain
    if path:
        m['path'] = path
    if secure:
        m['secure'] = ''

    c = c.output(header='').strip()
    print "set cookies", c
    _doc = doc()
    _doc.cookie = c

    return
    JS("""
    if (expires instanceof Date) expires = expires.getTime();
    if (pyjslib_isUndefined(domain)) domain = null;
    if (pyjslib_isUndefined(path)) path = null;
    if (pyjslib_isUndefined(secure)) secure = false;
    
    var today = new Date();
    var expiration = new Date();
    expiration.setTime(today.getTime() + expires)

    var c = encodeURIComponent(name) + '=' + encodeURIComponent(value);
    c += ';expires=' + expiration.toGMTString();

    if (domain)
        c += ';domain=' + domain;
    if (path)
        c += ';path=' + path;
    if (secure)
        c += ';secure';

    $doc.cookie = c;
    """)

def get_crumbs():
    docCookie = doc().cookie
    c = SimpleCookie(docCookie)
    c = c.output(header='')
    return map(strip, c.split('\n'))

def loadCookies():
    pass
