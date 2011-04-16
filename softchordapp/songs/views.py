# Create your views here.

from jsonrpc import *
from songs.models import Song 
from django.shortcuts import render_to_response

service = JSONRPCService()

@jsonremote(service)
def getAllSongs(request):
    #song_list = []
    #for song in Song.objects.all():
    #    song_list.append( ("TEMP", song.id) ]
    #return song_list
    
    return [(str(song),song.id) for song in Song.objects.all()]
    #return json_convert(Song.objects.all())

    
@jsonremote(service)
def addSong(request, idFromJson):
    s = Song()
    s.title = idFromJson
    s.save()
    return getAllSongs(request)

@jsonremote(service)
def deleteSong(request, idFromJson):
    s = Song.objects.get(id=idFromJson)
    s.delete()
    return getAllSongs(request)


