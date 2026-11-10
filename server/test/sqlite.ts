import { DatabaseSync } from "node:sqlite";

import type { Prepared, SqlDatabase } from "../src/db.ts";

type SqlValue = string | number | null;

interface StatementSync {
  run(...params: SqlValue[]): { changes: number | bigint };
  get(...params: SqlValue[]): unknown;
}

export function openSqlite(migrationSql: string): SqlDatabase {
  const db = new DatabaseSync(":memory:");
  db.exec("PRAGMA foreign_keys = ON");
  db.exec(migrationSql);
  return {
    prepare(sql: string): Prepared {
      const statement = db.prepare(sql) as StatementSync;
      const bound = (params: SqlValue[]): Prepared => ({
        bind(...values: SqlValue[]) {
          return bound(values);
        },
        async first<T>() {
          const row = statement.get(...params);
          return (row ?? null) as T | null;
        },
        async run() {
          const result = statement.run(...params);
          return { changes: Number(result.changes) };
        },
      });
      return bound([]);
    },
  };
}
