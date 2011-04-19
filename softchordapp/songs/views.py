# Create your views here.

from jsonrpc import *
from songs.models import DBSong, DBSongChord
from django.shortcuts import render_to_response

service = JSONRPCService()


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
    for song in DBSong.objects.all():
        song_list.append( (song.id, song.number, song.title) )
    # Send the list of songs to the front end:
    return song_list


@jsonremote(service)
def getSong(request, song_id):
    """
    Gets called by the front end to retreive a Song of the given ID from the database.
    """
    try:
        song = DBSong.objects.get(id=song_id)
    except Songs.DoesNotExist:
        raise
    
    # Fetch all the chords for this song:
    chords = []
    DBSongChord.objects.all()
    for chord in DBSongChord.objects.filter(song_id=song_id):
        chords.append(chord)
    
    return song_to_dict(song, chords)
    

@jsonremote(service)
def addSong(request, titleFromJson):
    """
    Gets called by the front end to add a song with the given title to the database.
    """
    
    # Create a new song database object:
    s = DBSong()
    s.title = titleFromJson
    # Save to the database:
    s.save()

    # Send a list of all songs to the front end:
    return getAllSongs(request)

@jsonremote(service)
def deleteSong(request, idFromJson):
    """
    Gets called by the frontend to delete a song with the given ID from the database.
    """

    # Delete the song from the database:
    s = DBSong.objects.get(id=idFromJson)
    s.delete()

    # Send a list of all songs to the front end:
    return getAllSongs(request)


