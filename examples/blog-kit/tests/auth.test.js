/**
 * Tests for password hashing, users, sessions, and roles.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { openDatabase } from '../db.js';
import {
  createUser, verifyUser, createSession, sessionUser, deleteSession,
  setUserRole, atLeast, signToken, unsignToken,
} from '../auth.js';

/** Opens an isolated in-memory database. */
function memdb() {
  return openDatabase(':memory:');
}

test('registers the first user as admin and the rest as readers', () => {
  const db = memdb();
  assert.equal(createUser(db, 'root', 'password-1').role, 'admin');
  assert.equal(createUser(db, 'ann', 'password-2').role, 'reader');
});

test('rejects duplicate usernames and weak input', () => {
  const db = memdb();
  createUser(db, 'ann', 'password-1');
  assert.throws(() => createUser(db, 'ann', 'password-2'), (e) => e.code === 409);
  assert.throws(() => createUser(db, 'x', 'password-1'), (e) => e.code === 422);
  assert.throws(() => createUser(db, 'bob', 'short'), (e) => e.code === 422);
});

test('verifies correct credentials and rejects wrong ones', () => {
  const db = memdb();
  createUser(db, 'ann', 'password-1');
  assert.equal(verifyUser(db, 'ann', 'password-1').username, 'ann');
  assert.equal(verifyUser(db, 'ann', 'wrong-pass'), null);
  assert.equal(verifyUser(db, 'nobody', 'password-1'), null);
});

test('resolves a session cookie to its user and ends it on logout', () => {
  const db = memdb();
  const created = createUser(db, 'ann', 'password-1');
  const signed = createSession(db, created.id);
  assert.equal(sessionUser(db, signed).username, 'ann');
  deleteSession(db, signed);
  assert.equal(sessionUser(db, signed), null);
});

test('rejects a forged session cookie signature', () => {
  const db = memdb();
  const created = createUser(db, 'ann', 'password-1');
  const signed = createSession(db, created.id);
  const forged = signed.slice(0, -1) + (signed.endsWith('0') ? '1' : '0');
  assert.equal(unsignToken(forged), null);
  assert.equal(sessionUser(db, forged), null);
  assert.ok(unsignToken(signToken('abc')) === 'abc');
});

test('changes roles through the admin rule and compares role levels', () => {
  const db = memdb();
  const ann = createUser(db, 'ann', 'password-1');
  assert.equal(setUserRole(db, ann.id, 'author').role, 'author');
  assert.throws(() => setUserRole(db, ann.id, 'superuser'), (e) => e.code === 422);
  assert.throws(() => setUserRole(db, 9999, 'author'), (e) => e.code === 404);
  assert.ok(atLeast('admin', 'author') && atLeast('author', 'author') && !atLeast('reader', 'author'));
});
