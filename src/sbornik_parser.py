
# -*- coding: utf-8 -*-


import sqlite3


db_file = "song_database.sqlite"

# This will be used for Python (sqlite3) operations:
curs = sqlite3.connect(db_file)



# Key: note text, value: note ID
note_text_id_dict = {}

for row in curs.execute("SELECT id, text, alt_text FROM notes"):
    #print 'row:', row
    id = row[0]
    text = row[1]
    alt_text = row[2]
    
    note_text_id_dict[text] = id
    note_text_id_dict[alt_text] = id

    
# Key: chord type text, value: chord type ID
chord_type_texts_dict = {}

for row in curs.execute("SELECT id, print FROM chord_types"):
    #print 'row:', row
    id = row[0]
    print_text = row[1]

    chord_type_texts_dict[print_text] = id
    if print_text == 'sus4':
        chord_type_texts_dict['sus'] = id
    




def convert_chord(chord_str):
    """
    Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
    """
    
    input_chord_str = chord_str[:]
    
    # FIXME
    in_paranthesis = chord_str.startswith('(') and chord_str.endswith(')')
    if in_paranthesis:
        chord_str = chord_str[1:-1]
    
    marker = None
    
    colon = chord_str.find(':')
    if colon != -1:
        if colon == len(chord_str)-1:
            raise ValueError("Not a chord (nothing after a colon")
            #print 'WARNING not a chord (nothing after a colon):', chord_str.encode('utf-8')
            #print '  INPUT CHORD:', input_chord_str.encode('utf-8')
            #return None
        
        marker = chord_str[:colon]
        chord_str = chord_str[colon+1:]
    
    if marker:
        print 'MARKER:', marker.encode('utf-8')
    
    slash = chord_str.find('/')
    if slash != -1:
        bass = chord_str[slash+1:]
        chord_str = chord_str[:slash]
    else:
        bass = None
    
    if chord_str[0] == u'Е': # Russian letter
        chord_str = 'E' + chord_str[1:]
    if chord_str[0] == u'С': # Russian letter
        chord_str = 'C' + chord_str[1:]
    if chord_str[0] == u'В': # Russian letter
        chord_str = 'B' + chord_str[1:]
    if chord_str[0] == u'А': # Russian letter
        chord_str = 'A' + chord_str[1:]

    #print 'chord_str after bass removal:', chord_str.encode('utf-8')
    if chord_str[0] in [u'A', u'B', u'C', u'D', u'E', u'F', u'G']:
        if len(chord_str) > 1 and chord_str[1] in [u'#', u'b', u'♭', u'♯']:
            note = chord_str[:2]
            type = chord_str[2:]
        else:
            note = chord_str[0]
            type = chord_str[1:]
    else:
        raise ValueError("First chord letter is not a note")
        #print 'WARNING first chord letter is not a note:', chord_str.encode('utf-8')
        #print '  INPUT CHORD:', input_chord_str.encode('utf-8')
        #return None
    
    #print '      ', note, '  ', type, '  ', bass

    if len(note) > 1:
        if note[1] == u'#':
            note = note[0] + u'♯'
        elif note[1] == u'b':
            note = note[0] + u'♭'
    if bass and len(bass) > 1:
        if bass[1] == u'#':
            bass = bass[0] + u'♯'
        elif bass[1] == u'b':
            bass = bass[0] + u'♭'
    
    #if bass:
    #    print 'converting:', note.encode('utf-8'), type, bass.encode('utf-8')
    #else:
    #    print 'converting:', note.encode('utf-8'), type, 'None'

    note_id = note_text_id_dict[note]
    if bass != None:
        bass_id = note_text_id_dict[bass]
    else:
        bass_id = -1
    
    try:
        type_id = chord_type_texts_dict[type]
    except KeyError:
        raise ValueError("Unkown chord type")
        #print 'WARNING: unknown chord type:', type.encode('utf-8')
        #print '  INPUT CHORD:', input_chord_str.encode('utf-8')
        #return None
    
    return (note_id, type_id, bass_id, in_paranthesis, marker)

    #print '  note:', note_id
    #print '  type:', type_id
    #print '  bass:', bass_id





sbornik_file = "zvuki_neba.txt"

all_songs = []


song_num = 0
song_title = None
song_lines = []

lines = []
for line in open(sbornik_file):
    # Convert to Unicode:
    lines.append( line.decode('utf-8') )


for linenum, line in enumerate(lines):
    
    next_song_num = song_num + 1
    if line.startswith("%s\t" % next_song_num) or line.strip() == str(next_song_num) or line.startswith("%s   " % next_song_num):
        all_songs.append( (song_num, song_title, song_lines) )

        title = lines[linenum+2].strip()
        if title[-1] in ['.', ',']:
            title = title[:-1]
        if title.startswith('1. '):
            title = title[3:]
        
        song_title = title
        song_num += 1
    else:
        if song_num > 0:
            # This is not the text before the first song
            while line.startswith('\t'):
                line = line[1:]
            song_lines.append(line[:-1])
        
all_songs.append( (song_num, song_title, song_lines) )



out_lines = [] # each item is a tuple of line text and chord list.


for song_num, song_title, song_lines in all_songs:
    #print '\nSONG', song_num, song_title
    
    prev_chords = None

    for line in song_lines:
        
        # Attempt to convert the line to chords:
        num_chords = 0
        num_non_chords = 0
        
        tmp_chords = []
        tmp_warnings = []

        for word in line.split():
            if word == u'/':
                num_chords += 1
                converted_chord = None
            else:
                try:
                    converted_chord = convert_chord(word)
                except ValueError, err:
                    tmp_warnings.append( 'WARNING: %s CHORD "%s"' % (str(err), word.encode('utf-8')) )
                    num_non_chords += 1
                else:
                    num_chords += 1
                    tmp_chords.append(converted_chord)
        

        print '\nnum_chords:', num_chords, 'num_non_chords:', num_non_chords
        if num_chords > num_non_chords:
            print 'CHORD LINE:', line.encode('utf-8')
            # This is a chords line
            prev_chords = tmp_chords
            for warning_str in tmp_warnings:
                print '  ', warning_str
        else:
            print 'LYRICS LINE:', line.encode('utf-8')
            # This is a lyrics line
            if prev_chords:
                out_lines.append( (line, prev_chords) )
            else:
                # The line before was NOT a chords line - no chords for this lyrics line
                out_lines.append( (line, []) )
            prev_chords = None


for lyrics, chords in out_lines:
    print '\nCHORDS:', chords
    print 'LYRICS:', lyrics.encode('utf-8')
    
    




