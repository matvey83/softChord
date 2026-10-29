"""Monospace chord lines shared with the iOS viewer.

Paired with softChord Viewer/softChord Viewer/softchord_text.swift.
place_chord_on_line and format_song_text stay in this order.
"""


def place_chord_on_line(cells, anchor, chord_text):
    """Write one chord into a monospace lyric line, centered on anchor.

    cells is one character per lyric column. An even-length name is shifted
    so the anchor letter sits just left of the name's middle. The name is
    moved inward when it would hang off either end of the line.

    Mirror: softchord_text.swift SongText.place.
    """
    chord_len = len(chord_text)
    chord_left = anchor - (chord_len // 2)
    if not (chord_len % 2):
        chord_left += 1
    chord_right = chord_left + chord_len

    while chord_left < 0:
        chord_left += 1
        chord_right += 1

    while chord_right >= len(cells):
        chord_right -= 1
        chord_left -= 1

    for i, char in enumerate(chord_text):
        cells[i + chord_left] = char


def format_song_text(lines, include_chords, line_has_chords, chords_on_line):
    """Clipboard text for one song. Chord lines need a monospace font.

    Mirror: softchord_text.swift SongText.render.
    chords_on_line(line_number) yields (anchor, chord text) for that line.
    """
    song_text = ''
    for linenum, line_text in enumerate(lines):
        if include_chords and line_has_chords(linenum):
            cells = [' '] * len(line_text)
            for anchor, chord_text in chords_on_line(linenum):
                place_chord_on_line(cells, anchor, chord_text)
            song_text += ''.join(cells).rstrip() + "\n"

        if not include_chords:
            line_text = line_text.rstrip()
        song_text += line_text + "\n"

    if song_text[-1] == "\n":
        song_text = song_text[:-1]

    return song_text.replace('\n', '\r\n')


def lyric_renumber_map(previous, text):
    """Old letter index to the index of that same letter after a text edit.

    The unchanged start and the unchanged end of the text keep their letters.
    A letter that was deleted or replaced has no entry, so the chord on it is
    dropped. The end is never allowed to reach into the start, so two old
    letters never map to one new letter (Hello -> Helo keeps one l).

    Mirror: softchord_text.swift SongLyricChords.renumberMap.
    """
    renumber_map = {}
    shortest = min(len(previous), len(text))

    prefix = 0
    while prefix < shortest and previous[prefix] == text[prefix]:
        renumber_map[prefix] = prefix
        prefix += 1

    suffix = 0
    while (suffix < shortest - prefix
           and previous[-1 - suffix] == text[-1 - suffix]):
        renumber_map[len(previous) - 1 - suffix] = len(text) - 1 - suffix
        suffix += 1
    return renumber_map


def line_start_index(text, index):
    """Index of the first character of the line that holds index."""
    return text.rfind("\n", 0, max(index, 0)) + 1


def line_letter_range(text, index):
    """(first, last) letter indexes of the line that holds index, or None.

    None when index is a line break, or is not in the text. A chord can only
    sit on a letter of its own line.

    Mirror: softchord_text.swift SongLyricChords.letterRange.
    """
    if index < 0 or index >= len(text) or text[index] == "\n":
        return None
    first = line_start_index(text, index)
    line_break = text.find("\n", index)
    last = len(text) - 1 if line_break < 0 else line_break - 1
    return first, last


def next_free_character(text, target, direction, occupied,
                        allow_other_direction=False):
    """The letter a chord lands on when it is moved onto target.

    A chord that is moved onto a letter that has a chord jumps over it, and
    over every other letter that has a chord, to the next free letter of the
    line in direction (+1 right, -1 left). Chords are never lost and a letter
    never gets two. When there is no free letter that way,
    allow_other_direction tries the other way (a drag does, an arrow key does
    not). None means the chord does not move.

    occupied holds the letters that have a chord, without the chord that moves.

    Mirror: softchord_text.swift SongLyricChords.nextFreeCharacter.
    """
    span = line_letter_range(text, target)
    if span is None:
        return None
    first, last = span
    step = -1 if direction < 0 else 1
    steps = (step, -step) if allow_other_direction else (step, )
    for each_step in steps:
        position = target
        while first <= position <= last:
            if position not in occupied:
                return position
            position += each_step
    return None


def chord_drag_direction(text, chord_char, previous_char, target):
    """+1 or -1: which way a chord dragged onto target goes past a chord.

    The mouse moved from the letter previous_char to target. A target on a
    different line than the chord goes forward (+1), as does no movement.

    Mirror: softchord_text.swift SongLyricChords.dragDirection.
    """
    if line_start_index(text, chord_char) != line_start_index(text, target):
        return 1
    return -1 if target < previous_char else 1
