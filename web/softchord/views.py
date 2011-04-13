# -*- coding: utf-8 -*-

# These are imported for Python 3 compatability:
# Use Unicode for all strings:
from __future__ import unicode_literals
from __future__ import division


from models import Songs, SongChordLink
from django.shortcuts import render_to_response



chord_types_list = [
  (0, u"Major", u""),
  (1, u"Minor", u"m"),
  (2, u"Suspended 4th", u"sus4"),
  (3, u"Major 7th", u"M7"),
  (4, u"Minor 7th", u"m7"),
  (5, u"Dominant 7th", u"7"),
  (6, u"Add 9", u"9"),
  (7, u"Diminished", u"dim"),
  (8, u"Major 6th", u"6"),
  (9, u"Minor 6th", u"m6"),
  (10, u"11th", u"11"),
  (11, u"Diminished", u"°"),
  (12, u"Diminished 7th", u"°7"),
]


global_notes_list = [
  (0, u"C", u"C"),
  (1, u"C♯", u"D♭"),
  (2, u"D", u"D"),
  (3, u"D♯", u"E♭"),
  (4, u"E", u"E"),
  (5, u"F", u"F"),
  (6, u"F♯", u"G♭"),
  (7, u"G", u"G"),
  (8, u"G♯", u"A♭"),
  (9, u"A", u"A"),
  (10, u"A♯", u"B♭"),
  (11, u"B", u"B"), 
]


# Make a list of all chord types:
chord_type_names = []
chord_type_prints = []
for chord_type_id, name, print_text in chord_types_list:
    chord_type_names.append(name)
    chord_type_prints.append(print_text)

"""

alternative_type_names = {
   "sus" : "sus4",
   "s4" : "sus4",
   "maj7" : "M7",
   "2" : "9",
   "(7)" : "7",
   "dim" : "°",
   "dim7" : "°7",
}

# Key: chord type text, value: chord type ID
chord_type_texts_dict = {}
for id, print_text in enumerate(chord_type_prints):
    chord_type_texts_dict[print_text] = id
    for alternative_name, official_name in alternative_type_names.iteritems():
        if print_text == official_name:
            chord_type_texts_dict[alternative_name] = id
"""

# Make a list of all notes and keys:
notes_list = []
note_text_id_dict = {}
for note_id, text, alt_text in global_notes_list:
    notes_list.append( (text, alt_text) )
    note_text_id_dict[text] = note_id
    note_text_id_dict[alt_text] = note_id



PREFER_SHARPS, PREFER_FLATS, PREFER_NEITHER = range(3)

def get_sharp_flat_preference(chords):

    num_prefer_sharp = 0
    num_prefer_flat = 0
    for chord in chords:
        if chord.note_id in [1, 6]: # C# or F#
            num_prefer_sharp += 1
        elif chord.note_id in [3, 10]: # Eb or Bb
            num_prefer_flat += 1
    
    if num_prefer_sharp > num_prefer_flat:
        return PREFER_SHARPS
    elif num_prefer_sharp < num_prefer_flat:
        return PREFER_FLATS
    else:
        return PREFER_NEITHER



def get_note_string(note_id, prefer_sharps_or_flats):
    """
    Returns the specified note as a string, using sharps vs flats
    as appropriate.
    """
    
    note_text, note_alt_text = notes_list[note_id]
    
    if prefer_sharps_or_flats == PREFER_SHARPS:
        return note_text
    elif prefer_sharps_or_flats == PREFER_FLATS:
        return note_alt_text
    else:
        if note_id in [1, 6]:
            # C#, F#
            return note_text
        else:
            # Bb, Eb, Ab
            return note_alt_text




def get_chord_text(chord, prefer_sharps_or_flats):
    """
    Returns string of the chord.
    For example, "Fm" or "Bbsus4"
    """
    
    note_text = get_note_string(chord.note_id, prefer_sharps_or_flats)
    
    chord_type_text = chord_type_prints[chord.chord_type_id]
    
    # Convert the chord note and type to a text string:
    if chord.marker: # Not NULL
        # Add the chord prefix (example: "1:", "2:")
        chord_str = '%s:%s%s' % (chord.marker, note_text, chord_type_text)
    else:
        chord_str = '%s%s' % (note_text, chord_type_text)
    
    # Add the bass note (if any):
    if chord.bass_note_id != -1: # Not NULL
        bass_note_text = get_note_string(chord.bass_note_id, prefer_sharps_or_flats)
        chord_str += "/%s" % bass_note_text
    
    # Add parentheses (if any):
    if chord.in_parentheses:
        chord_str = "(%s)" % chord_str
    
    return chord_str



    





def view_song(request, song_id):
    
    song_id = int(song_id)

    # Find the song in the database:
    try:
        song = Songs.objects.get(id=song_id)
    except Songs.DoesNotExist:
        song_name = "Does not exist"
        song_lines = [] # FIXME does not work for some reason ????
        prev_id = next_id = song_id
    else:
        song_name = song.title
        song_text = song.text

        chords = []
        SongChordLink.objects.all()
        subset = SongChordLink.objects.filter(song_id=song_id)
        for chord in subset:
            chords.append(chord)
        
        
        prefer_sharps_or_flats = get_sharp_flat_preference(chords)
        
        # Make a dict of chord strings (keyed by chord position in the song text:
        chord_texts_by_char_nums = {}
        for chord in chords:
            chord_song_char_num = chord.character_num
            #chord_text = chord.getChordText()
            chord_text = get_chord_text(chord, prefer_sharps_or_flats)
            
            # Replace "♯" with "#" and "♭" with "b":
            #chord_text = chord_text.replace("♯", "#").replace("♭", "b")
            
            chord_texts_by_char_nums[chord_song_char_num] = chord_text
        
        
        # Convert the song into a list of (chords, lyrics), for each line:
        song_lines = []
        
        curr_line_lyrics = []
        curr_line_chords = []
        for curr_char_num, char in enumerate(song_text):
            if char == "\n":
                song_lines.append( (curr_line_chords, curr_line_lyrics) )
                curr_line_lyrics = []
                curr_line_chords = []
            else:
                curr_line_chords.append( chord_texts_by_char_nums.get(curr_char_num, "") )
                curr_line_lyrics.append(char)
        
        if curr_line_lyrics:
            # If last line was not blank:
            song_lines.append( (curr_line_chords, curr_line_lyrics) )
        
        
        # Find the next ID (forward):
        next_id = song_id + 1
        while True:
            try:
                song = Songs.objects.get(id=next_id)
            except Songs.DoesNotExist:
                next_id += 1
                if next_id == 1000:
                    # This is the last song
                    next_id = song_id
                    break
            else:
                break
        
        # Find the next ID (backward):
        prev_id = song_id - 1
        while True:
            try:
                song = Songs.objects.get(id=prev_id)
            except Songs.DoesNotExist:
                prev_id -= 1
                if prev_id == 0:
                    # This is the first song
                    prev_id = song_id
                    break
            else:
                break
    
    # URLS for the Previous & Next buttons:
    prev_url = "../%i" % prev_id
    next_url = "../%i" % next_id
    
    return render_to_response("view_song.html", {"prev_url":prev_url, "next_url":next_url, "song_name":song_name, "song_lines":song_lines})



#def add_song(request):
#    return render_to_response("add_song.html", {} #"song_name":song_name, "song_text":song_text})





def view_all(request):
    """
    Display the table of contents page
    """
    
    song_list = []

    q = Songs.objects.all().order_by("id")
    for song in q:
        id = song.id
        num = song.number
        title = song.title
        song_list.append( (id, num, title) )

    
    # URLS for the Previous & Next buttons:
    #prev_url = "../%i" % prev_id
    #next_url = "../%i" % next_id
    
    return render_to_response("table_of_contents.html", {"song_list":song_list})










