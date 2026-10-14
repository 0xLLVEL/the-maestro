/**
 * End-to-end tests for every acceptance criterion over HTTP.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../server.js';

let base = '';
let server = null;

/** Starts the app on an ephemeral port with an isolated database. */
before(async () => {
  const app = createApp(':memory:');
  server = app.server;
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

/** Minimal cookie jar for the test client. */
const jars = new Map();

/** Sends JSON, keeping cookies per named client. */
async function api(client, method, path, body) {
  const res = await fetch(base + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(jars.get(client) ? { Cookie: jars.get(client) } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const setCookie = res.headers.get('set-cookie');
  if (setCookie) jars.set(client, setCookie.split(';')[0]);
  return { status: res.status, json: await res.json() };
}

/** Registers a user and returns the client name holding its session. */
async function registerAs(name, username, password) {
  const res = await api(name, 'POST', '/api/v1/auth/register', { username, password });
  assert.equal(res.status, 201);
  return name;
}

test('creates the first user as admin', async () => {
  await registerAs('admin', 'root', 'password-1');
  const me = await api('admin', 'POST', '/api/v1/auth/login', { username: 'root', password: 'password-1' });
  assert.equal(me.json.data.role, 'admin');
});

test('sets a session cookie on login', async () => {
  await registerAs('ann', 'ann', 'password-1');
  const before = jars.get('ann');
  await api('ann', 'POST', '/api/v1/auth/login', { username: 'ann', password: 'password-1' });
  assert.ok(jars.get('ann') && jars.get('ann').startsWith('sid=') && jars.get('ann') !== before);
});

test('answers 403 when a reader creates a post', async () => {
  const res = await api('ann', 'POST', '/api/v1/posts', { title: 'x', body: 'y' });
  assert.equal(res.status, 403);
  assert.equal(res.json.error.code, 'FORBIDDEN');
});

test('keeps drafts invisible until published', async () => {
  await registerAs('bob', 'bob', 'password-1');
  await api('admin', 'PATCH', '/api/v1/users/3', { role: 'author' });
  const created = await api('bob', 'POST', '/api/v1/posts', { title: 'Draft', body: 'work in progress' });
  assert.equal(created.status, 201);
  const id = created.json.data.id;
  const anon = await fetch(base + '/api/v1/posts');
  assert.ok(!(await anon.json()).data.posts.some((p) => p.id === id));
  const published = await api('bob', 'PATCH', `/api/v1/posts/${id}`, { status: 'published' });
  assert.equal(published.status, 200);
  const listed = await (await fetch(base + '/api/v1/posts')).json();
  assert.ok(listed.data.posts.some((p) => p.id === id));
});

test('answers 403 when editing someone else post', async () => {
  await registerAs('cat', 'cat', 'password-1');
  await api('admin', 'PATCH', '/api/v1/users/4', { role: 'author' });
  const res = await api('cat', 'PATCH', '/api/v1/posts/1', { title: 'hijack' });
  assert.equal(res.status, 403);
});

test('paginates the public list with page links data', async () => {
  for (let n = 0; n < 24; n += 1) {
    await api('bob', 'POST', '/api/v1/posts', { title: `Post ${n}`, body: 'bulk', status: 'published' });
  }
  const page2 = await (await fetch(base + '/api/v1/posts?page=2&per_page=10')).json();
  assert.equal(page2.data.posts.length, 10);
  assert.equal(page2.data.page, 2);
  assert.ok(page2.data.total >= 25);
});

test('renders a post page with title, body, author, and date', async () => {
  const res = await fetch(base + '/posts/1');
  const html = await res.text();
  assert.equal(res.status, 200);
  assert.ok(html.includes('Draft') && html.includes('bob'));
});

test('applies role changes on the next request', async () => {
  const changed = await api('admin', 'PATCH', '/api/v1/users/3', { role: 'admin' });
  assert.equal(changed.json.data.role, 'admin');
  const created = await api('bob', 'POST', '/api/v1/posts', { title: 'After promotion', body: 'b', status: 'published' });
  assert.equal(created.status, 201);
});
