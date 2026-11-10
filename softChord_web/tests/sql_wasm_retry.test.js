// sql-wasm.js keeps one init promise. A failed load must not be that promise
// forever, or the next songbook open never reaches SQLite.

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const initSqlJs = require("../sql-wasm.js");

test("a failed sql.js load is not reused", async function () {
  await assert.rejects(function () {
    return initSqlJs({
      locateFile: function () { return path.join(__dirname, "no-such-sql.wasm"); },
    });
  });
  var SQL = await initSqlJs({
    locateFile: function (file) { return path.join(__dirname, "..", file); },
  });
  var db = new SQL.Database();
  var rows = db.exec("SELECT 1 AS ok");
  db.close();
  assert.deepEqual(rows[0].values, [[1]]);
});
