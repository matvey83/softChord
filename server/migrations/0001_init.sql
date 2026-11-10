-- Login tables. Plain SQL, applied by wrangler for local D1.
-- consumed_at is null while a login token can still be used. A timestamp means
-- the token was used, or voided because a newer link was requested.

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL
);

CREATE TABLE login_tokens (
  token_hash TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  client TEXT NOT NULL CHECK (client IN ('web', 'ios', 'desktop')),
  verifier_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  consumed_at INTEGER
);

CREATE INDEX idx_login_tokens_email_created
  ON login_tokens (email, created_at);

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users (id),
  created_at INTEGER NOT NULL,
  last_used_at INTEGER NOT NULL,
  client TEXT NOT NULL CHECK (client IN ('web', 'ios', 'desktop')),
  device_label TEXT
);

CREATE INDEX idx_sessions_user ON sessions (user_id);
