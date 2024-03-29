# -*- coding: utf-8 -*-

import codecs

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

alternative_type_names = {
    "sus": "sus4",
    "s4": "sus4",
    "maj7": "M7",
    "2": "9",
    "(7)": "7",
    "dim": "°",
    "dim7": "°7",
}

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

# Key: chord type text, value: chord type ID
chord_type_texts_dict = {}
for id, print_text in enumerate(chord_type_prints):
    chord_type_texts_dict[print_text] = id
    for alternative_name, official_name in alternative_type_names.iteritems():
        if print_text == official_name:
            chord_type_texts_dict[alternative_name] = id

# Make a list of all notes and keys:
notes_list = []
note_text_id_dict = {}
for note_id, text, alt_text in global_notes_list:
    notes_list.append((text, alt_text))
    note_text_id_dict[text] = note_id
    note_text_id_dict[alt_text] = note_id

import sys


def convert_chord(chord_str):
    """
    Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
    """

    in_parentheses = False
    marker = None

    slash = chord_str.find('/')
    if slash != -1:
        bass = chord_str[slash + 1:]
        chord_str = chord_str[:slash]
    else:
        bass = None

    if chord_str[0] in [u'A', u'B', u'C', u'D', u'E', u'F', u'G']:
        if len(chord_str) > 1 and chord_str[1] in [u'#', u'b', u'♭', u'♯']:
            note = chord_str[:2]
            type = chord_str[2:]
        else:
            note = chord_str[0]
            type = chord_str[1:]
    else:
        raise ValueError("First chord letter is not a note")


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

    note_id = note_text_id_dict[note]
    if bass != None:
        bass_id = note_text_id_dict[bass]
    else:
        bass_id = -1

    try:
        type_id = chord_type_texts_dict[type]
    except KeyError:
        raise ValueError("Unkown chord type")

    return (marker, note_id, type_id, bass_id, in_parentheses)


if __name__ == "__main__":

    song_title = None
    filename = sys.argv[1].decode('utf-8')

    song_text = codecs.open(filename, 'rU', encoding='utf_8_sig').readlines()

    tmp_warnings = []
    song_lines = []

    for line in song_text:
        line = line.rstrip()  # Remove the EOL character(s)

        if line.startswith('#'):
            # Comment
            continue

        if line.startswith('{') and line.endswith('}'):
            custom_string = line[1:-1]
            if custom_string.startswith('title:'):
                song_title = custom_string[6:]
                print('TITLE: "%s"' % song_title)
            elif custom_string.startswith('t:'):
                song_title = custom_string[2:]
                print('TITLE: "%s"' % song_title)
            else:
                print('CUSTOM:', custom_string)
                tmp_warnings.append('WARNING: line ignored: "%s"' % line)
            continue

        line_lyrics = ""
        line_chords = []
        curr_chord = None
        curr_adjusted_char_num = 0

        for line_char_num, char in enumerate(line):
            if char == '[':
                curr_chord = ""
                continue

            if curr_chord != None:
                if char == ']':
                    line_chords.append((curr_adjusted_char_num, curr_chord))
                    curr_chord = None
                else:
                    curr_chord += char
                continue

            line_lyrics += char
            curr_adjusted_char_num += 1

        chords_dict = {}

        for char_num, chord_text in line_chords:
            try:
                converted_chord = convert_chord(chord_text)
            except ValueError as err:
                tmp_warnings.append('WARNING: %s CHORD "%s"' %
                                    (str(err), word.encode('utf-8')))
            else:
                chords_dict[char_num] = converted_chord

        print('')
        song_lines.append((line_lyrics, chords_dict))

    for warning_str in tmp_warnings:
        print('  ', warning_str)

    # Combine all lines together:
    global_song_text = ""
    global_song_chords = {}  # key: position in the global_song_text
    line_start_char_num = 0
    for lyrics, chords_dict in song_lines:
        global_song_text += lyrics + '\n'
        for line_char_num, chord in chords_dict.iteritems():
            song_char_num = line_char_num + line_start_char_num
            global_song_chords[song_char_num] = chord

        line_start_char_num += len(lyrics) + 1  # 1 for the EOL character
    # Go to next song

#EOF
