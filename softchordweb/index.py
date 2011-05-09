#!/usr/bin/python

import web
from network import JSONRPCService, jsonremote
import os

try:
    # NOTE: This uses sqlite3, which requires Python 2.5 or above
    # If this works, that means we are running locally
    db = web.database(dbn='sqlite', db='songs.songbook')
except Exception, err:
    # sqlite3 is not installed (we are on the server), try MySQLdb:
    db = web.database(dbn="mysql", host="softchord.db.6582285.hostedresource.com", db="softchord", user="softchord", pw="Concord123", charset=None, use_unicode=False)
    # NOTE: We MUST wet charset to None in order to work with version 1.2.0 of MySQLdb (installed on godaddy servers).
    # Also note that our web.py installtion is also modified to work with that version of MySQLdb.
    

urls = (
    '/rpc/',  'rpc', # For RPC calls (remote)
    '/songs/index.py/rpc/',  'rpc', # For RPC calls (local)
    '/songs/(.*)', 'static', # static content, e.g. the PyJamas-generated files (remote)
    '/(.*)', 'static', # static content, e.g. the PyJamas-generated files (local)
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
            # If simply /index.py/ is specified, load the main front-end page:
            name = 'softchordweb.html'
        
        ext = name.split(".")[-1]
        
        # Figure out what is the type of this static file:
        cType = {
            "js":"application/x-javascript",
            "txt":"text/plain",
            "css":"text/css",
            "html":"text/html",
            "png":"images/png",
            "jpg":"image/jpeg",
            "gif":"image/gif",
            "ico":"image/x-icon"            }
        
        # If this file is in static/output, then it's a PyJamas-generated file:
        if name in os.listdir('static/output'):
            path = 'static/output/%s' % name
            #return "ATTEMPTING TO READ: %s" % path
            web.header("Content-Type", cType[ext])
            return open(path, "rb").read()
        else:
            # If the static contents was not found
            web.notfound()
            return "NOT FOUND: %s" % name

service = JSONRPCService()

# Handler class for the jsonrpc service requests
class rpc:
    """
    Class for handling JSON-RPC requests
    """
    def POST(self):
        # Post a reply from our functions, the reply will get sent back to the client:
        return service(web.webapi.data())


# RPC function for testing the connection:
@jsonremote(service)
def echo(request, test_str):
    web.debug(repr(request))
    return "echo() result: %s" % test_str


#
# softChord-specific RPC functions:
#



@jsonremote(service)
def getAllSongs(request):
    """
    Gets called by the front end to retreive the list of songs in the database.
    """
    
    try:
        song_list = []
        results = db.select("songs")
        for row in results:
            song_list.append( (row.id, row.number, row.title) )
        # This list of songs will get converted to JSON and passed to the front-end (client):
        return song_list
    
    except Exception, err:
        # FIXME Implement a better way of informing the client of the error???
        return [ (0, 0, str(err)) ]

@jsonremote(service)
def getSong(request, song_id):
    """
    Gets called by the front end to retreive a Song of the given ID from the database.
    """
    
    results = db.select("songs", where="id=%s" % song_id)
    
    song_dict = None
    for row in results:
        song_dict = dict(row)
        break
    
    if row == None:
        return "SONG DOES NOT EXIST: %i" % song_id
    
    chords = []
    results = db.select("song_chord_link", where="song_id=%s" % song_id)
    for row in results:
        chords.append( dict(row) )
    
    song_dict["chords"] = chords
    
    # This song dict will get converted to JSON and passed to the front-end (client):
    return song_dict
    
    

app = web.application(urls, globals())

# Serve the content:
if __name__ == "__main__":
    try:
        app.run()
    except Exception, err:
        raise
        #print "Could not execute app.run()<br>EXCEPTION:", str(err)

