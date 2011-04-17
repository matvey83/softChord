
class HTTPRequest:

    def doCreateXmlHTTPRequest(self):
        if JS("""typeof $wnd.XMLHttpRequest != 'undefined'"""):
            # IE7+, Mozilla, Safari, ...
           return JS("""new XMLHttpRequest()""")

        # Check for IE6/ActiveX
        try:
            res = JS("""new ActiveXObject("Msxml2.XMLHTTP")""")
            return res
        except:
            pass
        return None

    def asyncImpl(self, method, user, pwd, url, postData, handler,
                      returnxml, content_type=None, headers=None):
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
        xmlHttp = self.doCreateXmlHTTPRequest()

        def onreadystatechange(evnt=None):
            global xmlHttp, handler
            if xmlHttp.readyState == 4:
                # For IE:
                JS("delete xmlHttp.onreadystatechange;")
                localHandler = handler
                status = xmlHttp.status
                if returnxml:
                    response = xmlHttp.responseXML
                else:
                    response = xmlHttp.responseText;
                handler = None
                xmlHttp = None
                if status == 200 or status == 0:
                    localHandler.onCompletion(response);
                else:
                    localHandler.onError(response, status);
        xmlHttp.onreadystatechange = onreadystatechange

        try:
            xmlHttp.open(method, url, True);
            for h in headers:
                if isinstance(headers[h], str):
                    xmlHttp.setRequestHeader(h, str(headers[h]))
                else:
                    hval = ';'.join([str(i) for i in headers[h]])
                    xmlHttp.setRequestHeader(h, hval)
            if postData is None:
                postData = ''
            xmlHttp.send(postData)
        except:
            # For IE:
            JS("delete xmlHttp.onreadystatechange;")
            localHandler = handler
            handler = None
            xmlHttp = None
            localHandler.onError(str(sys.exc_info()[1]), "");
            return False
        return True

