"""Chord names, transpose, and auto-detected key (no Qt)."""

PREFER_SHARPS, PREFER_FLATS, PREFER_NEITHER = range(3)

chord_types_list = [
    (0, "Major", ""),
    (1, "Minor", "m"),
    (2, "Suspended 4th", "sus4"),
    (3, "Major 7th", "M7"),
    (4, "Minor 7th", "m7"),
    (5, "Dominant 7th", "7"),
    (6, "Add 9", "9"),
    (7, "Augmented", "aug"),
    (8, "Major 6th", "6"),
    (9, "Minor 6th", "m6"),
    (10, "11th", "11"),
    (11, "Diminished", "°"),
    (12, "Diminished 7th", "°7"),
]

# Alternative text for chord types (for parsing text):
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
    (0, "C", "C"),
    (1, "C♯", "D♭"),
    (2, "D", "D"),
    (3, "D♯", "E♭"),
    (4, "E", "E"),
    (5, "F", "F"),
    (6, "F♯", "G♭"),
    (7, "G", "G"),
    (8, "G♯", "A♭"),
    (9, "A", "A"),
    (10, "A♯", "B♭"),
    (11, "B", "B"),
]

# Spellings used in the auto-detected key label (family-appropriate):
_NOTE_NAMES_SHARP = [
    "C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"
]
_NOTE_NAMES_FLAT = [
    "C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B"
]
_SHARP_MAJOR_TONICS = frozenset([7, 2, 9, 4, 11, 6])  # G D A E B F♯
_FLAT_MAJOR_TONICS = frozenset([5, 10, 3, 8, 1])  # F B♭ E♭ A♭ D♭
_MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
# Minor, minor 7th, minor 6th (chord_types_list ids):
_MINOR_CHORD_TYPE_IDS = frozenset([1, 4, 9])
_REGION_MIN_LEFT = 5
_REGION_MIN_RIGHT = 5
_REGION_LOOKAHEAD = 8
_REGION_SCORE_MARGIN = 1
_REGION_SPLIT_GAIN = 4
# Ignore a cut whose score gain is a small fraction of the one-key score
# (avoids chopping one song into Dm/C/Em/D from local ii–V–I motion).
_REGION_SPLIT_GAIN_RATIO = 0.2


def _chord_root_is_minor(chord):
    """Return (root_note_id, is_minor_quality). Slash bass (/C, /G, …) is ignored."""
    if hasattr(chord, "note_id"):
        return chord.note_id, chord.chord_type_id in _MINOR_CHORD_TYPE_IDS
    typ = chord[1]
    if isinstance(typ, bool):
        return chord[0], typ
    return chord[0], typ in _MINOR_CHORD_TYPE_IDS


def prefer_from_major_tonic(maj_tonic):
    if maj_tonic in _SHARP_MAJOR_TONICS:
        return PREFER_SHARPS
    if maj_tonic in _FLAT_MAJOR_TONICS:
        return PREFER_FLATS
    return PREFER_NEITHER


def score_key(chords, tonic, is_minor):
    """Higher is a better fit of these chord roots to tonic major/minor.

    A major (or other non-minor) V scores higher than a minor v, so a
    harmonic-minor cadence (E in Am, F♯ in Bm) beats the relative iv/v
    reading (Dm for Am, Em for Bm). A V→I (or V7→I) pair is extra
    evidence of the tonic, so Dm with A–Dm wins over Gm.
    """
    intervals = _MINOR_SCALE if is_minor else _MAJOR_SCALE
    scale = set((tonic + step) % 12 for step in intervals)
    dominant = (tonic + 7) % 12
    parsed = [_chord_root_is_minor(chord) for chord in chords]
    total = 0
    n = len(parsed)
    for i, (root, quality_minor) in enumerate(parsed):
        if root == tonic:
            total += 3
            if quality_minor == is_minor:
                total += 1
        elif root == dominant:
            # Minor v is a weak dominant; V / V7 is a cadence.
            total += 1 if quality_minor else 2
        elif root in scale:
            total += 1
        if i + 1 < n:
            next_root, next_minor = parsed[i + 1]
            if (root == dominant and not quality_minor
                    and next_root == tonic and next_minor == is_minor):
                total += 2
    return total


def family_score(chords, maj_tonic):
    """Best of this major key and its relative minor."""
    rel_minor = (maj_tonic - 3) % 12
    return max(score_key(chords, maj_tonic, False),
               score_key(chords, rel_minor, True))


def key_label(tonic, is_minor, prefer):
    names = _NOTE_NAMES_FLAT if prefer == PREFER_FLATS else _NOTE_NAMES_SHARP
    text = names[tonic]
    if is_minor:
        text += "m"
    return text


class DetectedKey:
    """One chosen key (relative major/minor already collapsed)."""

    def __init__(self, tonic, is_minor, prefer, label, score, margin, maj_tonic):
        self.tonic = tonic
        self.is_minor = is_minor
        self.prefer = prefer
        self.label = label
        self.score = score
        self.margin = margin
        self.maj_tonic = maj_tonic  # relative-major tonic (key signature)
        self.confident = margin >= _REGION_SCORE_MARGIN


def best_detected_key(chords):
    """Best key for a chord list; relative major/minor is a single key."""
    if not chords:
        return None
    ranked = []
    for maj_tonic in range(12):
        rel_minor = (maj_tonic - 3) % 12
        s_maj = score_key(chords, maj_tonic, False)
        s_min = score_key(chords, rel_minor, True)
        if s_maj >= s_min:
            tonic, is_minor, sc = maj_tonic, False, s_maj
        else:
            tonic, is_minor, sc = rel_minor, True, s_min
        prefer = prefer_from_major_tonic(maj_tonic)
        ranked.append((sc, maj_tonic, tonic, is_minor, prefer))
    ranked.sort(reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else (0, 0, 0, False, PREFER_NEITHER)
    margin = best[0] - second[0]
    sc, maj_tonic, tonic, is_minor, prefer = best
    return DetectedKey(tonic, is_minor, prefer, key_label(tonic, is_minor, prefer),
                       sc, margin, maj_tonic)


def detect_region_start_indices(chords):
    """Return chord-list indices where a new key region starts.

    Recursively pick the cut that most improves key scores vs treating the
    span as one key. Relative major/minor count as the same key.
    """
    def _splits(seq, offset):
        n = len(seq)
        if n < _REGION_MIN_LEFT + _REGION_MIN_RIGHT:
            return [offset]
        whole = best_detected_key(seq)
        whole_score = whole.score if whole else 0
        best_j = None
        best_gain = 0
        for j in range(_REGION_MIN_LEFT, n - _REGION_MIN_RIGHT + 1):
            left_key = best_detected_key(seq[:j])
            right_key = best_detected_key(seq[j:])
            if left_key is None or right_key is None:
                continue
            if left_key.maj_tonic == right_key.maj_tonic:
                continue
            # Each side must fit its own signature better than the other's.
            # (Global margin is not required: I–V–vi–IV can tie A with D
            # while still clearly not being B♭.)
            left_vs_right = left_key.score - family_score(seq[:j], right_key.maj_tonic)
            right_vs_left = right_key.score - family_score(seq[j:], left_key.maj_tonic)
            if left_vs_right < _REGION_SCORE_MARGIN:
                continue
            if right_vs_left < _REGION_SCORE_MARGIN:
                continue
            gain = left_key.score + right_key.score - whole_score
            # Prefer a later cut on a gain tie so the old key keeps the
            # last shared chord (e.g. D of A / I–V–vi–IV).
            if gain > best_gain or (gain == best_gain and best_j is not None):
                best_gain = gain
                best_j = j
        min_gain = _REGION_SPLIT_GAIN
        if whole_score:
            min_gain = max(min_gain, int(_REGION_SPLIT_GAIN_RATIO * whole_score))
        if best_j is None or best_gain < min_gain:
            return [offset]
        return (_splits(seq[:best_j], offset) +
                _splits(seq[best_j:], offset + best_j))

    if not chords:
        return []
    return _splits(chords, 0)


def auto_detected_key_labels(regions):
    """Unique consecutive key labels from (start_char, prefer, label) regions."""
    labels = []
    for item in regions:
        label = item[2]
        if not label:
            continue
        if not labels or labels[-1] != label:
            labels.append(label)
    return labels


def format_auto_detected_key_text(regions):
    """Build the UI string from (start_char, prefer, label) regions."""
    labels = auto_detected_key_labels(regions)
    if not labels:
        return "Auto-detected key:"
    return "Auto-detected key: " + ", ".join(labels)


def replace_russian_characeters(text):
    modified_text = ""

    # FIXME Use the built-in replace method instead
    for char in text:
        if char == 'Е':  # Russian letter
            char = 'E'
        if char == 'С':  # Russian letter
            char = 'C'
        if char == 'В':  # Russian letter
            char = 'B'
        if char == 'А':  # Russian letter
            char = 'A'
        if char == 'H':  # European style (H instead of B)
            char = 'B'
        if char == 'Н':  # Russian letter "N" (H instead of B)
            char = 'B'
        modified_text += char

    return modified_text


def transpose_note(note_id, steps):
    """
    Transpose the given note ID up by <steps>.
    Returns the transposed note ID.
    """
    note_id += steps

    if note_id < 0:
        note_id += 12
    elif note_id > 11:
        note_id -= 12

    return note_id


def convert_chord_from_string(chord_str, note_text_id_dict,
                              chord_type_texts_dict):
    """
    Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
    """
    if not chord_str:
        raise ValueError('Empty string')

    chord_str = replace_russian_characeters(chord_str)

    in_parentheses = chord_str.startswith('(') and chord_str.endswith(')')
    if in_parentheses:
        chord_str = chord_str[1:-1]

    marker = None

    colon = chord_str.find(':')
    if colon != -1:
        if colon == len(chord_str) - 1:
            raise ValueError("Not a chord (nothing after a colon")

        marker = chord_str[:colon]
        chord_str = chord_str[colon + 1:]

    slash = chord_str.find('/')
    if slash != -1:
        bass_str = chord_str[slash + 1:]
        chord_str = chord_str[:slash]
        if len(chord_str) == 0:
            raise ValueError("No characters present before the bass slash")
        if len(bass_str) == 0:
            raise ValueError("No character present after the bass slash")
    else:
        bass_str = None

    if chord_str[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        if len(chord_str) > 1 and chord_str[1] in ['#', 'b', '♭', '♯']:
            note = chord_str[:2]
            type = chord_str[2:]
        else:
            note = chord_str[0]
            type = chord_str[1:]
    else:
        raise ValueError("First chord letter is not a note")

    if len(note) > 1:
        if note[1] == '#':
            note = note[0] + '♯'
        elif note[1] == 'b':
            note = note[0] + '♭'
    if bass_str and len(bass_str) > 1:
        if bass_str[1] == '#':
            bass_str = bass_str[0] + '♯'
        elif bass_str[1] == 'b':
            bass_str = bass_str[0] + '♭'

    note_id = note_text_id_dict[note]
    if bass_str != None:
        try:
            bass_id = note_text_id_dict[bass_str]
        except KeyError:
            raise ValueError("Unrecognized bass note string")
    else:
        bass_id = -1

    try:
        type_id = chord_type_texts_dict[type]
    except KeyError:
        raise ValueError("Unkown chord type")

    return (marker, note_id, type_id, bass_id, in_parentheses)
