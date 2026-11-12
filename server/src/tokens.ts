const VERIFIER_HASH_SYNTAX = /^[0-9a-f]{64}$/;
const VERIFIER_SYNTAX = /^[A-Za-z0-9_-]{43,128}$/;

export function randomToken(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
}

export async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  const bytes = new Uint8Array(digest);
  let hex = "";
  for (const byte of bytes) hex += byte.toString(16).padStart(2, "0");
  return hex;
}

export function hashesEqual(left: string, right: string): boolean {
  if (!VERIFIER_HASH_SYNTAX.test(left) || !VERIFIER_HASH_SYNTAX.test(right)) return false;
  let diff = 0;
  for (let index = 0; index < left.length; index += 1) {
    diff |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return diff === 0;
}

export function isVerifier(value: string): boolean {
  return VERIFIER_SYNTAX.test(value);
}

export function isVerifierHash(value: string): boolean {
  return VERIFIER_HASH_SYNTAX.test(value);
}

/** Server-built link. The raw token is only in the fragment. */
export function buildLoginUrl(origin: string, client: string, hint: string, token: string): string {
  const url = new URL("/login", origin);
  url.searchParams.set("client", client);
  url.searchParams.set("hint", hint);
  url.hash = `t=${token}`;
  return url.href;
}
