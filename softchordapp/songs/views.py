# Create your views here.

from jsonrpc import *
from songs.models import Song 
from django.shortcuts import render_to_response

service = JSONRPCService()



@jsonremote(service)
def getAllSongs(request):
    """
    Gets called by the front end to retreive the list of songs in the database.
    """
    song_list = []
    for song in Song.objects.all():
        # Convert the Song object to dict:
        song_dict = song.__dict__
        del song_dict["_state"] # Used by django
        song_list.append(song_dict)

    # Send the list of songs to the front end:
    return song_list
    
    
@jsonremote(service)
def addSong(request, titleFromJson):
    """
    Gets called by the front end to add a song with the given title to the database.
    """
    s = Song()
    s.title = titleFromJson
    s.save()
    return getAllSongs(request)

@jsonremote(service)
def deleteSong(request, idFromJson):
    """
    Gets called by the frontend to delete a song with the given ID from the database.
    """
    s = Song.objects.get(id=idFromJson)
    s.delete()
    return getAllSongs(request)


