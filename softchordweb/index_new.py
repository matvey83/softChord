#!/usr/bin/python
# -*- coding: utf-8 -*-

import web
import json
import os
import songs

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
    '/songs/(.*)', 'SongHandler',
    '/static/(.*)', 'static', # static content, e.g. the PyJamas-generated files (local)
    '/', 'static', # static content, e.g. the PyJamas-generated files (local)
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
            #name = 'softchordweb.html'
            # Modified version of PyJamas-generated softchordweb.html that has
            # the title changed to "softChord Web":
            # name = 'softchordweb-custom.html'
            name = "index.html"
        
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
        # if name in os.listdir('static/output'):
        if name in os.listdir('static'):
            # path = 'static/output/%s' % name
            path = 'static/%s' % name
            #return "ATTEMPTING TO READ: %s" % path
            web.header("Content-Type", cType[ext])
            return open(path, "rb").read()
        else:
            # If the static contents was not found
            web.notfound()
            return "NOT FOUND: %s" % name





class SongHandler:
    def GET(self, path):
        if not path:
            song_list = []
            results = db.select("songs")
            for row in results:
                song_list.append( {"id":row.id, "number":row.number, "title":row.title} )
            # This list of songs will get converted to JSON and passed to the front-end (client):
            
            return json.dumps( song_list )
        
        try:
            song_num = int(path)
        except ValueError:
            return "ERROR: Song number must be an integer"
        
        # results = db.select("songs", where="id=%s" % song_id)
        results = db.select("songs", where="number=%s" % song_num)
        song_dict = None
        for row in results:
            song_dict = dict(row)
            break
        
        if row == None:
            return "SONG DOES NOT EXIST: %i" % song_id
        
        song_id = song_dict["id"]
        
        chords = []
        results = db.select("song_chord_link", where="song_id=%s" % song_id)
        for row in results:
            chords.append( dict(row) )
        
        song_dict["chords"] = chords
        
        # This song dict will get converted to JSON and passed to the front-end (client):

        song = songs.Song(song_dict)
        
        web.header('Content-Type','text/html; charset=utf-8', unique=True)           
        
        return song.getHtml()



    
app = web.application(urls, globals())

# Run the web.py's server, and serve the content:
if __name__ == "__main__":
    try:
        app.run()
    except Exception, err:
        raise

