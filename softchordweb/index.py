#!/usr/bin/python

import web
from network import JSONRPCService, jsonremote
import os

"""
# Requires Python 2.5 or above:
try:
    db = web.database(dbn='sqlite', db='songs.songbook')
except Exception, err:
    print "Content-type: text/html\n\n"
    print "Exception: %s" % (str(err))
"""
        
urls = (
    '/rpc/',  'rpc', # For the demo (remote)
    '/songs/index.py/rpc/',  'rpc', # For the demo (local)
    '/songs/(.*)', 'static', # static content (remote)
    '/(.*)', 'static', # static content (local)
)

# to wrap static content like this is possibly a bit of an unnecessary hack,
# but it makes me feel better.  as i am unfamiliar with web.py, i don't
# entirely know how it supports static content, so feel more comfortable
# with doing it manually, here, with this "static" class.

class static:
    def GET(self, name=None):
        """
        Get the static content of relative path "name"
        """
        
        if not name:
            # If simply /songs/ is specified, load the PyJamas main page:
            name = 'softchordweb.html'
        
        ext = name.split(".")[-1]

        cType = {
            "js":"application/x-javascript",
            "txt":"text/plain",
            "css":"text/css",
            "html":"text/html",
            "png":"images/png",
            "jpg":"image/jpeg",
            "gif":"image/gif",
            "ico":"image/x-icon"            }

        if name in os.listdir('static/output'):
            path = 'static/output/%s' % name
            #return "ATTEMPTING TO READ: %s" % path
            web.header("Content-Type", cType[ext])
            return open(path, "rb").read()
        else:
            web.notfound()
            return "NOT FOUND: %s" % name

service = JSONRPCService()

# a "wrapper" class around the jsonrpc service "service"
class rpc:
    """
    Class for handling JSON-RPC requests
    """
    def POST(self):
        return service(web.webapi.data())

# the two demo functions

@jsonremote(service)
def echo(request, user_name):
    web.debug(repr(request))
    return "echo() result: %s" % user_name

@jsonremote(service)
def reverse(request, user_name):
    return "reverse() result: %s" % user_name[::-1]




app = web.application(urls, globals())


if __name__ == "__main__":
    try:
        app.run()
    except Exception, err:
        raise
        #print "Could not execute app.run()<br>EXCEPTION:", str(err)

