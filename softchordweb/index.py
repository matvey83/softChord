#!/usr/bin/python

import web
from network import JSONRPCService, jsonremote
import os

try:
    # NOTE: This uses sqlite3, which requires Python 2.5 or above
    db = web.database(dbn='sqlite', db='songs.songbook')
except Exception, err:
    # sqlite3 is not installed (we are on the server), try MySQLdb:
    #print "Content-type: text/html\n\n"
    #print "Exception: %s" % (str(err))
    #db = web.database(dbn="mysql", db="softchord", user="softchord", password="Concord123")
    db = web.database(dbn="mysql", db="softchord.db.6582285.hostedresource.com", user="softchord", password="Concord123")
    

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




#
# softChord-specific RPC functions:
#


def song_to_dict(song, chords):
    """
    Convert the given Song object to a dict.
    (DBSong obj and a list of DBSongChord objects)
    This makes it easily convertable to JSON format to send to the server
    """

    # Convert the Song object to dict:
    song_dict = song.__dict__
    del song_dict["_state"] # Used by django
    
    chords_converted = []
    for chord in chords:
        chord_dict = chord.__dict__
        del chord_dict["_state"] # Used by django
        chords_converted.append(chord_dict)
    
    song_dict["chords"] = chords_converted
    
    return song_dict


@jsonremote(service)
def getAllSongs(request):
    """
    Gets called by the front end to retreive the list of songs in the database.
    """
    
    song_list = []
    results = db.select("songs") #, what="id,number,title")
    for row in results:
        print 'ROW:', row.id, row.number, row.title
        song_list.append( (row.id, row.number, row.title) )
    
    return song_list
    

@jsonremote(service)
def getSong(request, song_id):
    """
    Gets called by the front end to retreive a Song of the given ID from the database.
    """
    
    results = db.select("songs")
    
    song_dict = None
    for row in results:
        song_dict = dict(row)
        #song_dict["chords"] = []
        break
    
    if row == None:
        return "SONG DOES NOT EXIST: %i" % song_id
    
    chords = []
    results = db.select("song_chord_link", where="song_id=%s"%song_id)
    for row in results:
        chords.append( dict(row) )
    
    song_dict["chords"] = chords
    
    return song_dict
    
    
    # Fetch all the chords for this song:
    chords = []
    DBSongChord.objects.all()
    for chord in DBSongChord.objects.filter(song_id=song_id):
        chords.append(chord)
    
    return song_to_dict(song, chords)



app = web.application(urls, globals())


if __name__ == "__main__":
    try:
        app.run()
    except Exception, err:
        raise
        #print "Could not execute app.run()<br>EXCEPTION:", str(err)

