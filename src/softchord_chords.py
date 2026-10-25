"""Chord names, chord strings, transpose, and auto-detected key (no Qt).

Paired with softChord Viewer/softChord Viewer/softchord_chords.swift and
softChord_web/softchord_chords.js.
Shared functions stay in this order: prefer_from_major_tonic, score_key,
family_score, best_detected_key, detect_region_start_indices, transpose_note,
parse_chord, chord_string.

A chord is stored in the songbook as one string (see docs/chord_format.md).
parse_chord() is tolerant and never raises. Its behaviour is checked by
tests/chord_vectors.json in all three languages.
"""

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
    """Sharps, flats, or neither for this major key.

    Mirror: softchord_chords.swift SoftchordChords.preferFromMajorTonic.
    """
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

    Mirror: softchord_chords.swift SoftchordChords.scoreKey.
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
    """Best of this major key and its relative minor.

    Mirror: softchord_chords.swift SoftchordChords.familyScore.
    """
    rel_minor = (maj_tonic - 3) % 12
    return max(score_key(chords, maj_tonic, False),
               score_key(chords, rel_minor, True))


# TODO: The iPhone and web song pages should show this label. The editor's
# auto-detected key line stays as it is.
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
    """Best key for a chord list; relative major/minor is a single key.

    Mirror: softchord_chords.swift SoftchordChords.bestDetectedKey.
    """
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

    Mirror: softchord_chords.swift SoftchordChords.detectRegionStartIndices.
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
    """Move a note id up by the given number of half steps.

    steps can be negative. One call wraps a single octave. That wrap stays.
    The viewers fold any step count because they keep a running total.
    Mirror: softchord_chords.swift SoftchordChords.transposeNote.
    """
    note_id += steps

    if note_id < 0:
        note_id += 12
    elif note_id > 11:
        note_id -= 12

    return note_id


# ---------------------------------------------------------------------------
# Chord strings
# ---------------------------------------------------------------------------

UNKNOWN_CHORD_TEXT = "?"

# Semitone of each natural note name. The pitch of "E♯" or "C♭" comes from
# this, so spellings that are not in global_notes_list still parse.
_NATURAL_NOTE_IDS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ACCIDENTAL_SHIFT = {"♯": 1, "♭": -1}
_ACCIDENTAL_SYMBOL = {"#": "♯", "b": "♭", "♯": "♯", "♭": "♭"}


def _chord_type_texts():
    """Known suffix text -> chord_types_list id. Includes alternative names."""
    texts = {}
    for type_id, _name, print_text in chord_types_list:
        texts[print_text] = type_id
    for alternative, official in alternative_type_names.items():
        for type_id, _name, print_text in chord_types_list:
            if print_text == official:
                texts[alternative] = type_id
    return texts


_TYPE_ID_BY_SUFFIX = _chord_type_texts()


def classify_suffix(suffix):
    """Return (chord_type_id, is_known_type) for the text after the root.

    A known type is an exact match of a printed type or an alternative name.
    Any other suffix is still a chord: it counts as minor when it starts with
    m, min, mi or - (but not ma/maj), and as major otherwise. Callers keep
    the original suffix text for such chords.
    """
    if suffix in _TYPE_ID_BY_SUFFIX:
        return _TYPE_ID_BY_SUFFIX[suffix], True
    if suffix.startswith("-"):
        return 1, False
    if suffix.startswith("m") and not suffix.startswith("ma"):
        return 1, False
    return 0, False


def canonical_suffix(type_id):
    """Printed suffix of a chord_types_list id."""
    return chord_types_list[type_id][2]


def _note_id_from(letter, accidental_symbol):
    note_id = _NATURAL_NOTE_IDS[letter]
    if accidental_symbol:
        note_id = (note_id + _ACCIDENTAL_SHIFT[accidental_symbol]) % 12
    return note_id


def _read_note(text):
    """Split a leading note name off text.

    Returns (letter, accidental_symbol, rest) or None when text does not
    start with A-G (after the look-alike Russian letters are fixed).
    """
    if not text:
        return None
    letter = replace_russian_characeters(text[0])
    if letter not in _NATURAL_NOTE_IDS:
        return None
    rest = text[1:]
    accidental = ""
    if rest and rest[0] in _ACCIDENTAL_SYMBOL:
        accidental = _ACCIDENTAL_SYMBOL[rest[0]]
        rest = rest[1:]
    return letter, accidental, rest


class ParsedChord:
    """The fields of one chord string. Mirror: SoftchordChords.ParsedChord.

    unknown chords have no root; raw is the text to write back unchanged.
    note_id and bass_note_id are 0-11 (bass_note_id is -1 for none).
    chord_type_id is the chord_types_list id; when is_known_type is False it
    is only the base quality (0 major, 1 minor) and suffix holds the
    original text.
    """

    def __init__(self):
        self.unknown = True
        self.raw = UNKNOWN_CHORD_TEXT
        self.marker = ""
        self.in_parentheses = False
        self.root_text = ""
        self.note_id = -1
        self.suffix = ""
        self.chord_type_id = -1
        self.is_known_type = False
        self.bass_text = ""
        self.bass_note_id = -1

    @property
    def is_minor(self):
        return (not self.unknown) and self.chord_type_id in _MINOR_CHORD_TYPE_IDS


def parse_chord(text):
    """Parse a chord string. Tolerant: never raises, even for garbage.

    Layers: strip outer parentheses, the marker before the first colon and
    a valid slash bass note; the root must be A-G with an optional accidental
    (look-alike Russian letters are fixed, # and b become ♯ and ♭); the rest
    is the suffix. A suffix that is not a known type keeps its text. With no
    valid root the chord is unknown and keeps the raw text.

    Mirror: softchord_chords.swift SoftchordChords.parseChord.
    """
    parsed = ParsedChord()
    raw = (text or "").strip()
    parsed.raw = raw if raw else UNKNOWN_CHORD_TEXT

    body = raw
    parens = len(body) >= 2 and body.startswith("(") and body.endswith(")")
    if parens:
        body = body[1:-1]

    marker = ""
    colon = body.find(":")
    if colon != -1:
        marker = body[:colon]
        body = body[colon + 1:]

    note = _read_note(body)
    if note is None:
        return parsed
    letter, accidental, rest = note

    bass_text = ""
    bass_note_id = -1
    slash = rest.rfind("/")
    if slash != -1:
        bass = _read_note(rest[slash + 1:])
        if bass is not None and not bass[2]:
            bass_letter, bass_accidental, _ = bass
            bass_text = bass_letter + bass_accidental
            bass_note_id = _note_id_from(bass_letter, bass_accidental)
            rest = rest[:slash]

    type_id, known = classify_suffix(rest)
    parsed.unknown = False
    parsed.marker = marker
    parsed.in_parentheses = parens
    parsed.root_text = letter + accidental
    parsed.note_id = _note_id_from(letter, accidental)
    parsed.is_known_type = known
    parsed.chord_type_id = type_id
    parsed.suffix = canonical_suffix(type_id) if known else rest
    parsed.bass_text = bass_text
    parsed.bass_note_id = bass_note_id
    return parsed


def chord_string(marker, root_text, suffix, bass_text, in_parentheses):
    """Build the stored string of a known chord.

    Mirror: softchord_chords.swift SoftchordChords.chordString.
    """
    chord = root_text + suffix
    if marker:
        chord = "%s:%s" % (marker, chord)
    if bass_text:
        chord += "/" + bass_text
    if in_parentheses:
        chord = "(%s)" % chord
    return chord


def parsed_chord_string(parsed):
    """The canonical string for a ParsedChord. Unknown chords keep their raw."""
    if parsed.unknown:
        return parsed.raw
    return chord_string(parsed.marker, parsed.root_text, parsed.suffix,
                        parsed.bass_text, parsed.in_parentheses)


def convert_chord_from_string(chord_str):
    """Strict parse for imports: only a chord with a known type is accepted.

    Text and ChordPro import use this to tell chords from words, so "And" is
    not a chord. Raises ValueError otherwise. Returns
    (marker, note_id, chord_type_id, bass_note_id, in_parentheses).
    """
    if not chord_str:
        raise ValueError('Empty string')
    body = chord_str.strip()
    if len(body) >= 2 and body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    colon = body.find(":")
    if colon != -1:
        body = body[colon + 1:]
        if not body:
            raise ValueError("Marker with nothing after a colon")
    slash = body.rfind("/")
    if slash == 0:
        raise ValueError("Nothing before the bass slash")
    if slash != -1:
        bass = _read_note(body[slash + 1:])
        if not body[slash + 1:]:
            raise ValueError("Nothing after the bass slash")
        if bass is None or bass[2]:
            raise ValueError("Unrecognized bass note string")
    parsed = parse_chord(chord_str)
    if parsed.unknown:
        raise ValueError("First chord letter is not a note")
    if not parsed.is_known_type:
        raise ValueError("Unkown chord type")
    return (parsed.marker or None, parsed.note_id, parsed.chord_type_id,
            parsed.bass_note_id, parsed.in_parentheses)


# ---------------------------------------------------------------------------
# Spelling by key region, shared by the editor and the old-format converter
# ---------------------------------------------------------------------------


def note_text(note_id, prefer):
    """Spelling of a note id (0-11) for a sharps/flats preference."""
    text, alt_text = global_notes_list[note_id][1:]
    if prefer == PREFER_SHARPS:
        return text
    if prefer == PREFER_FLATS:
        return alt_text
    if note_id in (1, 6):  # C♯, F♯
        return text
    return alt_text  # B♭, E♭, A♭


def key_regions(chords):
    """Return [(start_char, prefer, key_label)] for chords with character_num,
    note_id and chord_type_id. Unknown chords must be left out.

    Mirror: softchord_text.swift SongText.regions.
    """
    chords = sorted(chords, key=lambda c: c.character_num)
    starts = detect_region_start_indices(chords)
    regions = []
    for k, idx in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(chords)
        group = chords[idx:end]
        detected = best_detected_key(group)
        start_char = group[0].character_num if group else 0
        if detected is None:
            prefer, label = PREFER_NEITHER, ""
        else:
            prefer, label = detected.prefer, detected.label
        regions.append((start_char, prefer, label))
    return regions


def prefer_at(regions, char_num):
    """Sharps/flats preference at a character, given key_regions()."""
    prefer = regions[0][1] if regions else PREFER_NEITHER
    for start_char, region_prefer, _label in regions:
        if char_num >= start_char:
            prefer = region_prefer
        else:
            break
    return prefer


class ChordFields:
    """One chord as separate fields (the old storage form)."""

    def __init__(self, character_num, note_id, chord_type_id, bass_note_id,
                 marker, in_parentheses, suffix=None, unknown_raw=None):
        self.character_num = character_num
        self.note_id = note_id
        self.chord_type_id = chord_type_id
        self.bass_note_id = bass_note_id
        self.marker = marker
        self.in_parentheses = in_parentheses
        # None means the printed text of chord_type_id.
        self.suffix = suffix
        # Set for a chord with no usable root. It is written as this text.
        self.unknown_raw = unknown_raw


def spelled_chord_strings(fields_list):
    """Chord strings for one song's ChordFields, spelled like the editor shows
    them (sharps or flats by key region). Returns one string per item.
    """
    known = [f for f in fields_list if f.unknown_raw is None]
    regions = key_regions(known)
    out = []
    for fields in fields_list:
        if fields.unknown_raw is not None:
            out.append(fields.unknown_raw or UNKNOWN_CHORD_TEXT)
            continue
        prefer = prefer_at(regions, fields.character_num)
        suffix = fields.suffix
        if suffix is None:
            suffix = canonical_suffix(fields.chord_type_id)
        bass_text = ""
        if fields.bass_note_id is not None and fields.bass_note_id >= 0:
            bass_text = note_text(fields.bass_note_id, prefer)
        out.append(
            chord_string(fields.marker or "",
                         note_text(fields.note_id, prefer), suffix, bass_text,
                         fields.in_parentheses))
    return out
