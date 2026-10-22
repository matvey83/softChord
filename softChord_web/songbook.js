// Read a .songbook SQLite file in the browser.
// load() is the part a future server replaces. It should call useSongs()
// with the same list: id, title, text, and chords anchored to character indexes.

(function (root, factory) {
  var songText = typeof root.SongText !== "undefined" ? root.SongText : require("./softchord_text");
  var api = factory(songText, root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.Songbook = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (SongText, root) {
  var songs = null;
  var byId = new Map();

  var SONGS_SQL = "SELECT id, title, text FROM songs ORDER BY id";
  var CHORDS_SQL = "SELECT song_id, character_num, note_id, chord_type_id, " +
    "bass_note_id, marker, in_parentheses FROM song_chord_link ORDER BY rowid";

  function normalizeMarker(marker) {
    if (marker == null || marker === "" || marker === "-1" || marker === "None") {
      return "";
    }
    return String(marker);
  }

  function normalizeChord(row) {
    return {
      characterNum: row.character_num,
      noteId: row.note_id,
      chordTypeId: row.chord_type_id,
      bassNoteId: row.bass_note_id == null ? -1 : row.bass_note_id,
      marker: normalizeMarker(row.marker),
      inParentheses: !!row.in_parentheses,
    };
  }

  function queryRows(db, sql) {
    var statement = db.prepare(sql);
    var found = [];
    try {
      while (statement.step()) {
        found.push(statement.getAsObject());
      }
    } finally {
      statement.free();
    }
    return found;
  }

  function songsFromRows(songRows, chordRows) {
    var chordsBySong = new Map();
    for (var i = 0; i < chordRows.length; i++) {
      var row = chordRows[i];
      var chords = chordsBySong.get(row.song_id);
      if (!chords) {
        chords = [];
        chordsBySong.set(row.song_id, chords);
      }
      chords.push(normalizeChord(row));
    }
    return songRows.map(function (row) {
      return {
        id: row.id,
        title: row.title || "",
        text: row.text || "",
        chords: chordsBySong.get(row.id) || [],
      };
    });
  }

  function useSongs(list) {
    songs = list;
    byId = new Map();
    for (var i = 0; i < list.length; i++) {
      byId.set(list[i].id, list[i]);
    }
  }

  function openBytes(SQL, bytes) {
    var db = new SQL.Database(bytes);
    try {
      var songRows = queryRows(db, SONGS_SQL);
      var chordRows = queryRows(db, CHORDS_SQL);
      useSongs(songsFromRows(songRows, chordRows));
    } catch (error) {
      var message = error && error.message ? error.message : String(error);
      throw new Error("The songbook could not be read. " + message);
    } finally {
      db.close();
    }
  }

  function locateWasm(file) {
    return file;
  }

  // Download the .songbook and query it here. A server can take this over
  // by returning the same song list and calling useSongs().
  function load(url) {
    if (typeof root.initSqlJs !== "function") {
      return Promise.reject(new Error("SQLite could not be loaded."));
    }
    return root.initSqlJs({ locateFile: locateWasm }).then(function (SQL) {
      return fetch(url, { cache: "no-store" }).then(function (response) {
        if (!response.ok) {
          throw new Error("The songbook could not be opened.");
        }
        return response.arrayBuffer();
      }).then(function (buffer) {
        openBytes(SQL, new Uint8Array(buffer));
      });
    }).catch(function (error) {
      var message = error && error.message ? error.message : String(error);
      if (message === "Failed to fetch" || message === "Load failed") {
        throw new Error(
          "The songbook could not be opened. Serve this page over http so it can read the .songbook file.");
      }
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(message);
    });
  }

  function requireSongs() {
    if (!songs) {
      throw new Error("The songbook could not be opened.");
    }
    return songs;
  }

  function copyChord(chord) {
    return {
      characterNum: chord.characterNum,
      noteId: chord.noteId,
      chordTypeId: chord.chordTypeId,
      bassNoteId: chord.bassNoteId,
      marker: chord.marker,
      inParentheses: chord.inParentheses,
    };
  }

  function titles() {
    return requireSongs().map(function (song) {
      return { id: song.id, title: song.title || "" };
    });
  }

  // A copy, so later chord or text edits do not change the loaded snapshot.
  function source(id) {
    requireSongs();
    var song = byId.get(id);
    if (!song) {
      throw new Error("That song is not in the songbook.");
    }
    return {
      id: song.id,
      title: song.title || "",
      text: song.text || "",
      chords: (song.chords || []).map(copyChord),
    };
  }

  function songText(id, includeChords) {
    var song = source(id);
    return SongText.render(song.text, song.chords, includeChords);
  }

  function sheet(id) {
    var song = source(id);
    return SongText.sheet(song.text, song.chords);
  }

  return {
    load: load,
    useSongs: useSongs,
    openBytes: openBytes,
    titles: titles,
    source: source,
    songText: songText,
    sheet: sheet,
  };
});
