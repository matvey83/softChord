
# -*- coding: utf-8 -*-


import sqlite3


db_file = "song_database.sqlite"

# This will be used for Python (sqlite3) operations:
curs = sqlite3.connect(db_file)



# Key: note text, value: note ID
note_text_id_dict = {}

for row in curs.execute("SELECT id, text, alt_text FROM notes"):
    print 'row:', row
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
    print '\ninput:', chord_str.encode('utf-8')
    
    colon = chord_str.find(':')
    if colon != -1:
        chord_str = chord_str[colon:]
    
    slash = chord_str.find('/')
    if slash != -1:
        bass = chord_str[slash+1:]
        chord_str = chord_str[:slash]
    else:
        bass = None
    
    print 'chord_str after bass removal:', chord_str.encode('utf-8')
    if chord_str[0] in [u'A', u'B', u'C', u'D', u'E', u'F', u'G']:
        if len(chord_str) > 1 and chord_str[1] in [u'#', u'b', u'♭', u'♯']:
            note = chord_str[:2]
            type = chord_str[2:]
        else:
            note = chord_str[0]
            type = chord_str[1:]
    else:
        return None

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
    
    if bass:
        print 'converting:', note.encode('utf-8'), type, bass.encode('utf-8')
    else:
        print 'converting:', note.encode('utf-8'), type, 'None'

    note_id = note_text_id_dict[note]
    if bass != None:
        bass_id = note_text_id_dict[bass]
    else:
        bass_id = -1
    
    type_id = chord_type_texts_dict.get(type, 'UNKNOWN')
    
    print '  note:', note_id
    print '  type:', type_id
    print '  bass:', bass_id





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



for song_num, song_title, song_lines in all_songs:
    #print '\nSONG', song_num, song_title
    
    prev_chords = None

    for line in song_lines:
        chord_line = True
        
        num_chords = 0
        num_non_chords = 0
        
        s = line.split()
        for chord_str in s:
            if chord_str[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                num_chords += 1
            else:
                num_non_chords += 1
            pass
        
        if num_chords > num_non_chords:
            line_chords = []
            for chord_str in s:
                if chord_str == '/':
                    # FIXME
                    continue
                
                converted_chord = convert_chord(chord_str)
                if converted_chord:
                    line_chords.append(converted_chord)

            prev_chords = line_chords
        else:
            if prev_chords:
                pass
                #print 'CHORDS:', prev_chords
            #print 'LINE:', line
            prev_chords = None


    
    
    




