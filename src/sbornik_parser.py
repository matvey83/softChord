
# -*- coding: utf-8 -*-



def convert_chord(note, type, bass):

    




sbornik_file = "zvuki_neba.txt"

all_songs = []


song_num = 0
song_title = None
song_lines = []

lines = open(sbornik_file).readlines()
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

                colon = chord_str.find(':')
                if colon != -1:
                    chord_str = chord_str[colon:]
                
                slash = chord_str.find('/')
                if slash != -1:
                    bass = chord_str[slash+1:]
                    chord_str = chord_str[:slash]
                else:
                    bass = None
                
                if chord_str[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    if len(chord_str) > 1 and chord_str[1] in ['#', 'b', '♭', '♯']:
                        note = chord_str[:1]
                    else:
                        note = chord_str[0]
                type = chord_str[1:]
                #print '      ', note, '  ', type, '  ', bass

                line_chords.append( (note, type, bass) )
            prev_chords = line_chords
        else:
            
            print '\n'
            if prev_chords:
                print 'CHORDS:', prev_chords
                
                converted_chords = []
                for note, type, bass in prev_chords:
                    converted_chord = convert_chord(note, type, bass)
                    if converted_chord:
                        converted_chords.append( converted_chord )
                    print 'converted:', converted_chords
            print 'LINE:', line
            prev_chords = None


    
    
    




