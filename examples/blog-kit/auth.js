/**
 * Authentication: password hashing, users, signed sessions, login rate limit.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { randomBytes, scryptSync, timingSafeEqual, createHmac } from 'node:crypto';

/** Session lifetime in milliseconds (7 days). */
const SESSION_TTL = 7 * 24 * 3600 * 1000;

/** Login attempts allowed per IP per window. */
const LOGIN_LIMIT = 50;
const LOGIN_WINDOW = 3600 * 1000;

/** Valid user roles, weakest first. */
export const ROLES = ['reader', 'author', 'admin'];

/** Per-process HMAC secret; sessions end on restart (documented in the PRD notes). */
const cookieSecret = randomBytes(32);

/** In-memory login attempt counters per IP. */
const attempts = new Map();

/** Records a login attempt and reports whether the IP is over the limit. */
export function loginAllowed(ip) {
  const now = Date.now();
  const hit = attempts.get(ip);
  if (!hit || hit.reset < now) {
    attempts.set(ip, { count: 1, reset: now + LOGIN_WINDOW });
    return true;
  }
  hit.count += 1;
  return hit.count <= LOGIN_LIMIT;
}

/** Validates a username (3-32 lowercase letters, digits, dash, underscore). */
export function validUsername(name) {
  return typeof name === 'string' && /^[a-z0-9_-]{3,32}$/.test(name);
}

/** Validates a password (at least 8 characters). */
export function validPassword(password) {
  return typeof password === 'string' && password.length >= 8;
}

/** Hashes a password with a fresh random salt. */
export function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const hash = scryptSync(password, salt, 64).toString('hex');
  return { salt, hash };
}

/** Compares a password against a stored salt and hash in constant time. */
export function checkPassword(password, salt, stored) {
  const hash = scryptSync(password, salt, 64);
  const expected = Buffer.from(stored, 'hex');
  return hash.length === expected.length && timingSafeEqual(hash, expected);
}

/**
 * Creates a user; the first user in the database becomes admin, the rest readers.
 */
export function createUser(db, username, password) {
  if (!validUsername(username)) throw Object.assign(new Error('Invalid username.'), { code: 422 });
  if (!validPassword(password)) throw Object.assign(new Error('Password is too short.'), { code: 422 });
  const count = db.prepare('SELECT COUNT(*) AS n FROM users').get().n;
  const role = count === 0 ? 'admin' : 'reader';
  const { salt, hash } = hashPassword(password);
  try {
    const row = db.prepare('INSERT INTO users (username, hash, salt, role) VALUES (?, ?, ?, ?) RETURNING id, username, role').get(username, hash, salt, role);
    return row;
  } catch {
    throw Object.assign(new Error('Username is taken.'), { code: 409 });
  }
}

/** Verifies credentials and returns the public user row, or null. */
export function verifyUser(db, username, password) {
  const row = db.prepare('SELECT id, username, hash, salt, role FROM users WHERE username = ?').get(username);
  if (!row || !checkPassword(password, row.salt, row.hash)) return null;
  return { id: row.id, username: row.username, role: row.role };
}

/** Signs a session token for the cookie value. */
export function signToken(token) {
  const sig = createHmac('sha256', cookieSecret).update(token).digest('hex');
  return `${token}.${sig}`;
}

/** Returns the token when the cookie signature is valid, else null. */
export function unsignToken(signed) {
  if (typeof signed !== 'string') return null;
  const dot = signed.lastIndexOf('.');
  if (dot < 1) return null;
  const token = signed.slice(0, dot);
  const presented = Buffer.from(signed.slice(dot + 1));
  const expected = Buffer.from(createHmac('sha256', cookieSecret).update(token).digest('hex'));
  if (presented.length !== expected.length || !timingSafeEqual(presented, expected)) return null;
  return token;
}

/** Creates a session row and returns the signed cookie value. */
export function createSession(db, userId) {
  const token = randomBytes(32).toString('hex');
  db.prepare('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)').run(token, userId, Date.now() + SESSION_TTL);
  return signToken(token);
}

/** Resolves a signed cookie value to the public user row, or null. */
export function sessionUser(db, signed) {
  const token = unsignToken(signed);
  if (!token) return null;
  const row = db.prepare(
    'SELECT u.id, u.username, u.role FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > ?'
  ).get(token, Date.now());
  return row || null;
}

/** Deletes the session behind a signed cookie value. */
export function deleteSession(db, signed) {
  const token = unsignToken(signed);
  if (token) db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
}

/** Changes a user's role; only valid roles are accepted. */
export function setUserRole(db, userId, role) {
  if (!ROLES.includes(role)) throw Object.assign(new Error('Unknown role.'), { code: 422 });
  const row = db.prepare('UPDATE users SET role = ? WHERE id = ? RETURNING id, username, role').get(role, userId);
  if (!row) throw Object.assign(new Error('User not found.'), { code: 404 });
  return row;
}

/** Reports whether a role reaches at least the required role. */
export function atLeast(role, required) {
  return ROLES.indexOf(role) >= ROLES.indexOf(required);
}
