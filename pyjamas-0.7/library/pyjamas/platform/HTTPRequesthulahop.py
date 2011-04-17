class XULrunnerHackCallback:
    def __init__(self, htr, mode, user, pwd, url, postData=None, handler=None,
                 return_xml=False, content_type=None, headers=None):
        print "XMLHttpRequest using xulrunner hack callback", mode, url
        self.htr = htr
        self.mode = mode
        self.user = user
        self.pwd = pwd
        self.url = url
        self.postData = postData
        self.handler = handler
        self.return_xml = return_xml
        self.content_type = content_type
        self.headers = headers

        pyjd.add_timer_queue(self.callback)

class HTTPRequest:
    # See HTTPRequest.py

    def asyncGet(self, url, handler, returnxml=False,
                 content_type=None, headers=None, user=None, pwd=None):
        """Does an asynchrounous 'GET' call. Differs from the GWT version
        such that the user and password arguments cannot be the first two
        arguments, and it takes some extra parameters"""
        postData = None
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncGet: handler is not a valid request handler")
        return XULrunnerHackCallback(self, 'GET', user, pwd, url, postData, 
                                     handler, returnxml, content_type, headers)

    def asyncPost(self, url, postData, handler, returnxml=False,
                  content_type=None, headers=None, user=None, pwd=None):
        """Does an asynchrounous 'POST' call. Differs from the GWT version
        such that the user and password arguments cannot be the first two
        arguments, and it takes some extra parameters"""
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncPost: handler is not a valid request handler")
        return XULrunnerHackCallback(self, 'POST', user, pwd, url, postData, 
                                     handler, returnxml, content_type, headers)

    def asyncDelete(self, url, handler, returnxml=False,
                    content_type=None, headers=None, user=None, pwd=None):
        """Does an asynchrounous 'DELETE' call. Differs from the GWT version
        such that the user and password arguments cannot be the first two
        arguments, and it takes some extra parameters"""
        postData = None
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncDelete: handler is not a valid request handler")
        return XULrunnerHackCallback(self, 'DELETE', user, pwd, url, postData, 
                                     handler, returnxml, content_type, headers)

    def asyncPut(self, url, postData, handler, returnxml=False,
                 content_type=None, headers=None, user=None, pwd=None):
        """Does an asynchrounous 'PUT' call. Differs from the GWT version
        such that the user and password arguments cannot be the first two
        arguments, and it takes some extra parameters"""
        if not hasattr(handler, 'onCompletion'):
            raise RuntimeError("Invalid call to asyncPut: handler is not a valid request handler")
        return XULrunnerHackCallback(self, 'PUT', user, pwd, url, postData, 
                                     handler, returnxml, content_type, headers)

