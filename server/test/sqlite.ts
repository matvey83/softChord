import { DatabaseSync } from "node:sqlite";

import type { Prepared, SqlDatabase } from "../src/db.ts";

type SqlValue = string | number | null;

interface StatementSync {
  run(...params: SqlValue[]): { changes: number | bigint };
  get(...params: SqlValue[]): unknown;
}

const runNow = Symbol("runNow");

type SqliteStatement = Prepared & { [runNow]?: () => { changes: number } };

export function openSqlite(migrationSql: string, options?: { yield?: boolean }): SqlDatabase {
  const db = new DatabaseSync(":memory:");
  db.exec("PRAGMA foreign_keys = ON");
  db.exec(migrationSql);
  const pause = async () => {
    if (options?.yield) await new Promise((resolve) => setImmediate(resolve));
  };
  return {
    prepare(sql: string): Prepared {
      const statement = db.prepare(sql) as StatementSync;
      const bound = (params: SqlValue[]): SqliteStatement => ({
        bind(...values: SqlValue[]) {
          return bound(values);
        },
        async first<T>() {
          await pause();
          const row = statement.get(...params);
          return (row ?? null) as T | null;
        },
        async run() {
          await pause();
          const result = statement.run(...params);
          return { changes: Number(result.changes) };
        },
        [runNow]() {
          const result = statement.run(...params);
          return { changes: Number(result.changes) };
        },
      });
      return bound([]);
    },
    async batch(statements: Prepared[]): Promise<Array<{ changes: number }>> {
      db.exec("BEGIN IMMEDIATE");
      try {
        const results = statements.map((statement) => {
          const run = (statement as SqliteStatement)[runNow];
          if (!run) throw new Error("cannot batch this statement");
          return run();
        });
        db.exec("COMMIT");
        return results;
      } catch (error) {
        db.exec("ROLLBACK");
        throw error;
      }
    },
  };
}
