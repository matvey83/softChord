// Zoom steps for the song area. The zoom is a whole percent (100 = normal),
// so repeated steps never drift the way 0.1 + 0.1 + 0.1 does.

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SongZoom = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var MIN = 50;
  var MAX = 300;
  var STEP = 10;
  var DEFAULT = 100;
  var STORAGE_KEY = "softchord.zoomPercent";

  function clamp(percent) {
    var n = Math.round(Number(percent));
    if (!isFinite(n)) {
      return DEFAULT;
    }
    return Math.min(MAX, Math.max(MIN, n));
  }

  // direction is +1 (zoom in) or -1 (zoom out). The result stays on the
  // 10% grid, so a stray stored 105 goes to 110 or 100 and not to 115.
  function stepped(percent, direction) {
    var current = clamp(percent);
    var next = direction > 0
      ? (Math.floor(current / STEP) + 1) * STEP
      : (Math.ceil(current / STEP) - 1) * STEP;
    return clamp(next);
  }

  // True when the song area is at its normal size (Reset zoom has nothing to do).
  function isDefault(percent) {
    return clamp(percent) === DEFAULT;
  }

  // A saved value is only trusted when it is a whole number in range.
  function parseStored(text) {
    if (typeof text !== "string" || !/^\d{2,3}$/.test(text)) {
      return DEFAULT;
    }
    var n = Number(text);
    return n >= MIN && n <= MAX ? n : DEFAULT;
  }

  function load(storage) {
    try {
      return parseStored(storage.getItem(STORAGE_KEY));
    } catch (error) {
      return DEFAULT;
    }
  }

  // Storage can be missing or full (private browsing): zoom still works then.
  function save(storage, percent) {
    try {
      storage.setItem(STORAGE_KEY, String(clamp(percent)));
    } catch (error) {
      // Not remembered, which is fine.
    }
  }

  return {
    MIN: MIN, MAX: MAX, STEP: STEP, DEFAULT: DEFAULT, STORAGE_KEY: STORAGE_KEY,
    clamp: clamp, stepped: stepped, isDefault: isDefault, parseStored: parseStored, load: load, save: save,
  };
});
