/**
 * HTTP layer: thin routes that call the auth and post services.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { openDatabase } from './db.js';
import {
  createUser, verifyUser, createSession, sessionUser, deleteSession,
  setUserRole, atLeast, loginAllowed,
} from './auth.js';
import { createPost, listPosts, getPost, updatePost, deletePost, parsePaging } from './posts.js';
import { authPage, listPage, detailPage, editorPage } from './views.js';

/** Maximum request body size in bytes. */
const MAX_BODY = 1024 * 1024;

/** Maps service error codes to HTTP status codes. */
const STATUS = { 401: 401, 403: 403, 404: 404, 409: 409, 422: 422 };

/** Maps service error codes to public error names. */
const NAMES = { 401: 'UNAUTHORIZED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 409: 'CONFLICT', 422: 'VALIDATION' };

/** Parses the cookie header into a key-value object. */
function parseCookies(header) {
  const out = {};
  for (const part of (header || '').split(';')) {
    const eq = part.indexOf('=');
    if (eq > 0) out[part.slice(0, eq).trim()] = decodeURIComponent(part.slice(eq + 1).trim());
  }
  return out;
}

/** Reads the request body up to the size cap. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY) reject(Object.assign(new Error('Body too large.'), { code: 422 }));
      else chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

/** Sends a JSON response with the given status. */
function sendJson(res, status, obj) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(obj));
}

/** Converts a service error into a uniform JSON error response. */
function sendError(res, err) {
  const status = STATUS[err.code] || 500;
  const code = NAMES[err.code] || 'INTERNAL';
  sendJson(res, status, { error: { code, message: status === 500 ? 'Internal error.' : err.message } });
}

/** Sets the signed session cookie on the response. */
function setCookie(res, signed) {
  res.setHeader('Set-Cookie', `sid=${signed}; HttpOnly; Path=/; SameSite=Lax`);
}

/** Clears the session cookie on the response. */
function clearCookie(res) {
  res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; Max-Age=0');
}

/** Redirects the browser to the given path. */
function redirect(res, path) {
  res.writeHead(302, { Location: path });
  res.end();
}

/**
 * Creates the application server bound to a database path (`:memory:` in tests).
 */
export function createApp(dbPath = 'blog.db') {
  const db = openDatabase(dbPath);
  const strings = JSON.parse(readFileSync(new URL('./lang/en.json', import.meta.url)));

  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      const user = sessionUser(db, parseCookies(req.headers.cookie).sid);
      const seg = url.pathname.split('/').filter(Boolean);

      if (req.method === 'GET' && url.pathname === '/styles.css') {
        res.writeHead(200, { 'Content-Type': 'text/css; charset=utf-8' });
        res.end(readFileSync(new URL('./styles.css', import.meta.url)));
        return;
      }
      if (req.method === 'GET' && url.pathname === '/') {
        const { page, perPage } = parsePaging(Object.fromEntries(url.searchParams));
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(listPage(listPosts(db, user, page, perPage), strings));
        return;
      }
      if (req.method === 'GET' && seg[0] === 'posts' && seg[1] !== undefined) {
        const post = getPost(db, user, Number(seg[1]));
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(detailPage(post));
        return;
      }
      if (req.method === 'GET' && (url.pathname === '/login' || url.pathname === '/register')) {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(authPage(url.pathname.slice(1)));
        return;
      }
      if (req.method === 'POST' && (url.pathname === '/login' || url.pathname === '/register')) {
        const form = new URLSearchParams(await readBody(req));
        const mode = url.pathname.slice(1);
        if (mode === 'register') {
          const created = createUser(db, form.get('username') || '', form.get('password') || '');
          setCookie(res, createSession(db, created.id));
        } else {
          const found = verifyUser(db, form.get('username') || '', form.get('password') || '');
          if (!found) {
            res.writeHead(401, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(authPage('login', strings['auth.invalid']));
            return;
          }
          setCookie(res, createSession(db, found.id));
        }
        redirect(res, '/');
        return;
      }
      if (req.method === 'GET' && url.pathname === '/logout') {
        deleteSession(db, parseCookies(req.headers.cookie).sid);
        clearCookie(res);
        redirect(res, '/');
        return;
      }
      if (url.pathname === '/editor') {
        if (!user || !atLeast(user.role, 'author')) {
          res.writeHead(403, { 'Content-Type': 'text/html; charset=utf-8' });
          res.end(strings['error.forbidden']);
          return;
        }
        if (req.method === 'GET') {
          const id = url.searchParams.get('id');
          const post = id ? getPost(db, user, Number(id)) : { title: '', body: '', status: 'draft' };
          res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
          res.end(editorPage(post));
          return;
        }
        const form = new URLSearchParams(await readBody(req));
        const patch = { title: form.get('title') || '', body: form.get('body') || '', status: form.get('status') || 'draft' };
        const id = url.searchParams.get('id');
        const saved = id ? updatePost(db, user, Number(id), patch)
          : createPost(db, user.id, patch.title, patch.body, patch.status);
        redirect(res, `/posts/${saved.id || id}`);
        return;
      }
      if (seg[0] === 'api' && seg[1] === 'v1') {
        await handleApi(req, res, url, seg.slice(2), user);
        return;
      }
      res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('Not found.');
    } catch (err) {
      if (req.url.startsWith('/api/')) sendError(res, err);
      else {
        res.writeHead(STATUS[err.code] || 500, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(err.code ? err.message : 'Internal error.');
      }
    }
  });

  /** Handles the JSON API routes with uniform success and error shapes. */
  async function handleApi(req, res, url, seg, user) {
    const need = (role) => {
      if (!user) throw Object.assign(new Error('Unauthorized.'), { code: 401 });
      if (!atLeast(user.role, role)) throw Object.assign(new Error('Forbidden.'), { code: 403 });
    };
    if (req.method === 'POST' && seg[0] === 'auth' && seg[1] === 'register') {
      const body = JSON.parse(await readBody(req));
      const created = createUser(db, body.username, body.password);
      setCookie(res, createSession(db, created.id));
      sendJson(res, 201, { data: created });
      return;
    }
    if (req.method === 'POST' && seg[0] === 'auth' && seg[1] === 'login') {
      if (!loginAllowed(req.socket.remoteAddress || '')) {
        sendJson(res, 429, { error: { code: 'RATE_LIMITED', message: 'Too many attempts.' } });
        return;
      }
      const body = JSON.parse(await readBody(req));
      const found = verifyUser(db, body.username, body.password);
      if (!found) {
        sendJson(res, 401, { error: { code: 'UNAUTHORIZED', message: 'Invalid credentials.' } });
        return;
      }
      setCookie(res, createSession(db, found.id));
      sendJson(res, 200, { data: found });
      return;
    }
    if (req.method === 'POST' && seg[0] === 'auth' && seg[1] === 'logout') {
      need('reader');
      deleteSession(db, parseCookies(req.headers.cookie).sid);
      clearCookie(res);
      sendJson(res, 200, { data: { ok: true } });
      return;
    }
    if (req.method === 'GET' && seg[0] === 'posts' && seg[1] === undefined) {
      const { page, perPage } = parsePaging(Object.fromEntries(url.searchParams));
      sendJson(res, 200, { data: listPosts(db, user, page, perPage) });
      return;
    }
    if (req.method === 'POST' && seg[0] === 'posts' && seg[1] === undefined) {
      need('author');
      const body = JSON.parse(await readBody(req));
      const created = createPost(db, user.id, body.title, body.body, body.status || 'draft');
      sendJson(res, 201, { data: created });
      return;
    }
    if (seg[0] === 'posts' && seg[1] !== undefined) {
      const id = Number(seg[1]);
      if (req.method === 'GET') {
        sendJson(res, 200, { data: getPost(db, user, id) });
        return;
      }
      if (req.method === 'PATCH') {
        need('author');
        const body = JSON.parse(await readBody(req));
        sendJson(res, 200, { data: updatePost(db, user, id, body) });
        return;
      }
      if (req.method === 'DELETE') {
        need('author');
        deletePost(db, user, id);
        sendJson(res, 200, { data: { ok: true } });
        return;
      }
    }
    if (req.method === 'PATCH' && seg[0] === 'users' && seg[1] !== undefined) {
      need('admin');
      const body = JSON.parse(await readBody(req));
      sendJson(res, 200, { data: setUserRole(db, Number(seg[1]), body.role) });
      return;
    }
    sendJson(res, 404, { error: { code: 'NOT_FOUND', message: 'Unknown endpoint.' } });
  }

  return { server, db };
}

const runDirectly = process.argv[1] && import.meta.url.endsWith('/server.js') && process.argv[1].endsWith('server.js');

/* c8 ignore start */
if (runDirectly) {
  const port = Number(process.env.PORT || 3000);
  const { server } = createApp(process.env.DB_PATH || 'blog.db');
  server.listen(port, () => console.log(`Blog on http://localhost:${port}`));
}
/* c8 ignore end */
