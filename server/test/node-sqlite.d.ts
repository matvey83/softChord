declare module "node:sqlite" {
  export class DatabaseSync {
    constructor(path: string);
    exec(sql: string): void;
    prepare(sql: string): {
      run(...params: Array<string | number | null>): { changes: number | bigint };
      get(...params: Array<string | number | null>): unknown;
    };
  }
}
