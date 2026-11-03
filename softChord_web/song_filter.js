// Title search. A blank query keeps every song, in the same order.
// Titles that start with the query come first, then titles that contain it,
// each group in the songbook's order.
// TODO: Also match the song number, the way the editor's song list filter does.
// Paired with softChord Viewer/softChord Viewer/SongFilter.swift.

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SongFilter = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function matching(query, songs) {
    var text = String(query).trim();
    if (!text) {
      return songs;
    }
    var needle = text.toLocaleLowerCase("en-US");
    var starts = [];
    var contains = [];
    songs.forEach(function (song) {
      var at = song.title.toLocaleLowerCase("en-US").indexOf(needle);
      if (at === 0) {
        starts.push(song);
      } else if (at !== -1) {
        contains.push(song);
      }
    });
    return starts.concat(contains);
  }

  return { matching: matching };
});
