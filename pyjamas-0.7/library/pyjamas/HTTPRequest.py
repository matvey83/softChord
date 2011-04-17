# This is the gtk-dependent HTTPRequest module.
# For the pyjamas/javascript version, see platform/HTTPRequestPyJS.py

import sys
import pygwt
from __pyjamas__ import JS
if sys.platform not in ['mozilla', 'ie6', 'opera', 'oldmoz', 'safari']:
    from __pyjamas__ import get_main_frame
    import pyjd

handlers = {}

class XULrunnerHackCallback:
    def __init__(self, htr, mode, user, pwd, url, postData=None, handler=None,
                 return_xml=False, content_type=None, headers = None):
        pass

    def callback(self):
        return self.htr.asyncImpl(self.mode, self.user, self.pwd, self.url,
                                  self.postData, self.handler, self.return_xml, 
                                  self.content_type, self.headers)


class HTTPRequest:
    def asyncGet(self, url, handler, returnxml=False, 
                 content_type=None, headers=None, user=None, pwd=None):
        postData = None
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncGet: handler is not a valid request handler")
        self.asyncImpl('GET', user, pwd, url, postData, handler,
                       returnxml, content_type, headers)

    def asyncPost(self, url, postData, handler, returnxml=False, 
                  content_type=None, headers=None, user=None, pwd=None):
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncPost: handler is not a valid request handler")
        return self.asyncImpl('POST', user, pwd, url, postData, handler,
                       returnxml, content_type, headers)

    def asyncDelete(self, url, handler, returnxml=False, 
                    content_type=None, headers=None, user=None, pwd=None):
        postData = None
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncDelete: handler is not a valid request handler")
        return self.asyncImpl('DELETE', user, pwd, url, postData, handler,
                       returnxml, content_type, headers)

    def asyncPut(self, url, postData, handler, returnxml=False, 
                 content_type=None, headers=None, user=None, pwd=None):
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncPut: handler is not a valid request handler")
        return self.asyncImpl('PUT', user, pwd, url, postData, handler,
                       returnxml, content_type, headers)

    def createXmlHTTPRequest(self):
        return self.doCreateXmlHTTPRequest()

    def doCreateXmlHTTPRequest(self):
        return get_main_frame().getXmlHttpRequest()

    def onLoad(self, sender, event, ignorearg):
        xmlHttp = event.target
        localHandler = handlers.get(xmlHttp)
        del handlers[xmlHttp]
        responseText = xmlHttp.responseText
        status = xmlHttp.status
        handler = None
        xmlHttp = None
        # XXX HACK! webkit wrapper returns 0 not 200!
        if status == 0:
            print "HACK ALERT! webkit wrapper returns 0 not 200!"
        if status == 200 or status == 0:
            localHandler.onCompletion(responseText)
        else :
            localHandler.onError(responseText, status)
        
    def onReadyStateChange(self, xmlHttp, event, ignorearg):
        try:
            xmlHttp = get_main_frame().gobject_wrap(xmlHttp) # HACK!
        except:
            pass # hula / XUL
        print xmlHttp.readyState
        if xmlHttp.readyState != 4:
            return
        # TODO - delete xmlHttp.onreadystatechange
        localHandler = handlers.get(xmlHttp)
        del handlers[xmlHttp]
        responseText = xmlHttp.responseText
        print "headers", xmlHttp.getAllResponseHeaders()
        status = xmlHttp.status
        handler = None
        xmlHttp = None
        print "status", status
        print "local handler", localHandler
        # XXX HACK! webkit wrapper returns 0 not 200!
        if status == 0:
            print "HACK ALERT! webkit wrapper returns 0 not 200!"
        if status == 200 or status == 0:
            localHandler.onCompletion(responseText)
        else :
            localHandler.onError(responseText, status)
        
    def _convertUrlToAbsolute(self, url):

        uri = pygwt.getModuleBaseURL()
        if url[0] == '/':
            # url is /somewhere.
            sep = uri.find('://')
            if not uri.startswith('file://'):
                
                slash = uri.find('/', sep+3)
                if slash > 0:
                    uri = uri[:slash]

            return "%s%s" % (uri, url)

        else:
            if url[:7] != 'file://' and url[:7] != 'http://' and \
               url[:8] != 'https://':
                slash = uri.rfind('/')
                return uri[:slash+1] + url

        return url

    def asyncImpl(self, method, user, pwd, url, postData, handler,
                  returnxml=False, content_type=None, headers=None):
        if headers is None:
            headers = {}
        if user and pwd and not "Authorization" in headers:
            import base64
            headers["Authorization"] = 'Basic %s' % (base64.b64encode('%s:%s' % (user, pwd)))

        if postData is not None and not "Content-Length" in headers:
            headers["Content-Length"] = str(len(postData))
        if content_type is not None:
            headers["Content-Type"] = content_type
        if not "Content-Type" in headers:
            if returnxml:
                headers["Content-Type"] = "application/xml; charset=utf-8"
            else:
                headers["Content-Type"] = "text/plain; charset=utf-8"

        #for c in Cookies.get_crumbs():
        #    xmlHttp.setRequestHeader("Set-Cookie", c)
        #    print "setting cookie", c

        mf = get_main_frame()
        xmlHttp = self.doCreateXmlHTTPRequest()
        url = self._convertUrlToAbsolute(url)
        print "xmlHttp", method, user, pwd, url, postData, handler, dir(xmlHttp)
        #try :
        if mf.platform == 'webkit' or mf.platform == 'mshtml':
            xmlHttp.open(method, url, True, '', '')
        else:
            # EEK!  xmlhttprequest.open in xpcom is a miserable bastard.
            #xmlHttp.open("POST", url, True, '', '')
            print url, xmlHttp.open(method, url)
        for h in headers:
            if isinstance(headers[h], str):
                xmlHttp.setRequestHeader(h, headers[h])
            else:
                hval = ';'.join([str(i) for i in headers[h]])
                xmlHttp.setRequestHeader(h, hval)
        #if not "Set-Cookie" in headers:
        #    headers["Set-Cookie"] = []
        #for c in Cookies.get_crumbs():
        #    headers["Set-Cookie"].append(c)
        #    print "setting cookie", c

        if mf.platform == 'webkit' or mf.platform == 'mshtml':
            mf._addXMLHttpRequestEventListener(xmlHttp, "onreadystatechange",
                                         self.onReadyStateChange)
        else:
            mf._addXMLHttpRequestEventListener(xmlHttp, "load",
                                         self.onLoad)
        handlers[xmlHttp] = handler
        xmlHttp.send(postData)

        return True

        #except:
            #del xmlHttp.onreadystatechange
        handler = None
        xmlHttp = None
        localHandler.onError(str(e))
        return False

