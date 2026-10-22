// Title search. A blank query keeps every song, in the same order.
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
    return songs.filter(function (song) {
      return song.title.toLocaleLowerCase("en-US").indexOf(needle) !== -1;
    });
  }

  return { matching: matching };
});
