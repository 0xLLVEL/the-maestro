// Simple blog: auth + posts + pagination. Run: node blog.js
const { createServer } = require('node:http');
const { DatabaseSync } = require('node:sqlite');
const { randomBytes, scryptSync, createHmac } = require('node:crypto');

const db = new DatabaseSync('blog.db');
db.exec(`CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, hash TEXT, salt TEXT, role TEXT DEFAULT 'reader');
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, expires_at INTEGER);
CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, author_id INTEGER, title TEXT, body TEXT, status TEXT DEFAULT 'draft', created_at INTEGER, updated_at INTEGER);`);

const SECRET = randomBytes(32);
const css = `<style>body{font-family:Arial;background:#f5f5f5;color:#222;margin:0}main{max-width:700px;margin:auto;padding:20px}article{background:#fff;padding:15px;margin-bottom:10px;border-radius:8px}input,textarea,select{display:block;width:100%;margin:5px 0 10px;padding:8px}button{background:#06c;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer}</style>`;
const page = (t, b) => `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${t}</title>${css}</head><body><main>${b}</main></body></html>`;

function hash(pw, salt) { return scryptSync(pw, salt, 64).toString('hex'); }
function sign(t) { return t + '.' + createHmac('sha256', SECRET).update(t).digest('hex'); }
function cookies(h) { const o = {}; (h || '').split(';').forEach(p => { const i = p.indexOf('='); if (i > 0) o[p.slice(0, i).trim()] = p.slice(i + 1).trim(); }); return o; }
function me(req) {
  const c = cookies(req.headers.cookie).sid || '';
  const t = c.split('.')[0];
  const row = t ? db.prepare(`SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?`).get(t, Date.now()) : null;
  return row || null;
  // TODO: verify cookie signature
}
function body(req) { return new Promise(res => { let d = ''; req.on('data', c => d += c); req.on('end', () => res(d)); }); }

const server = createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const user = me(req);
  const J = (s, o) => { res.writeHead(s, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(o)); };
  const H = (s, h) => { res.writeHead(s, { 'Content-Type': 'text/html' }); res.end(h); };

  if (u.pathname === '/' && req.method === 'GET') {
    const pg = Math.max(1, parseInt(u.searchParams.get('page') || '1'));
    const per = 10;
    const rows = db.prepare(`SELECT p.*, u.username AS author FROM posts p JOIN users u ON u.id=p.author_id WHERE status='published' ORDER BY created_at DESC LIMIT ? OFFSET ?`).all(per, (pg - 1) * per);
    const total = db.prepare(`SELECT COUNT(*) n FROM posts WHERE status='published'`).get().n;
    let h = '<h1>My Blog</h1>';
    if (!rows.length) h += '<p>No posts yet.</p>';
    rows.forEach(p => { h += `<article><h2><a href="/posts/${p.id}">${p.title}</a></h2><p>by ${p.author}</p></article>`; });
    for (let i = 1; i <= Math.ceil(total / per); i++) h += `<a href="/?page=${i}">${i}</a> `;
    return H(200, page('My Blog', h));
  }
  if (u.pathname.startsWith('/posts/') && req.method === 'GET') {
    const p = db.prepare(`SELECT p.*, u.username AS author FROM posts p JOIN users u ON u.id=p.author_id WHERE p.id=?`).get(u.pathname.split('/')[2]);
    if (!p || (p.status !== 'published' && (!user || (user.id !== p.author_id && user.role !== 'admin')))) return H(404, page('404', '<h1>Not found</h1>'));
    return H(200, page(p.title, `<article><h1>${p.title}</h1><p>by ${p.author}</p><div>${p.body}</div></article>`));
  }
  if ((u.pathname === '/login' || u.pathname === '/register') && req.method === 'GET') {
    const m = u.pathname.slice(1);
    return H(200, page(m, `<h1>${m}</h1><form method="post" action="/${m}"><input name="username"><input name="password" type="password"><button>${m}</button></form>`));
  }
  if ((u.pathname === '/login' || u.pathname === '/register') && req.method === 'POST') {
    const f = new URLSearchParams(await body(req));
    if (u.pathname === '/register') {
      const n = db.prepare('SELECT COUNT(*) n FROM users').get().n;
      const salt = randomBytes(16).toString('hex');
      try { db.prepare('INSERT INTO users (username, hash, salt, role) VALUES (?,?,?,?)').run(f.get('username'), hash(f.get('password'), salt), salt, n === 0 ? 'admin' : 'reader'); }
      catch { return H(200, page('error', '<p>Username taken</p>')); }
      const id = db.prepare('SELECT id FROM users WHERE username=?').get(f.get('username')).id;
      const t = randomBytes(32).toString('hex');
      db.prepare('INSERT INTO sessions VALUES (?,?,?)').run(t, id, Date.now() + 7 * 864e5);
      res.writeHead(302, { Location: '/', 'Set-Cookie': `sid=${sign(t)}; HttpOnly; Path=/` }); return res.end();
    }
    const r = db.prepare('SELECT * FROM users WHERE username=?').get(f.get('username'));
    if (!r || hash(f.get('password'), r.salt) !== r.hash) return H(200, page('error', '<p>Invalid username or password.</p>'));
    const t = randomBytes(32).toString('hex');
    db.prepare('INSERT INTO sessions VALUES (?,?,?)').run(t, r.id, Date.now() + 7 * 864e5);
    res.writeHead(302, { Location: '/', 'Set-Cookie': `sid=${sign(t)}; HttpOnly; Path=/` }); return res.end();
  }
  if (u.pathname === '/editor') {
    if (!user || (user.role !== 'author' && user.role !== 'admin')) return H(200, page('error', '<p>Forbidden.</p>'));
    if (req.method === 'GET') {
      const id = u.searchParams.get('id');
      const p = id ? db.prepare('SELECT * FROM posts WHERE id=?').get(id) : { title: '', body: '', status: 'draft' };
      return H(200, page('Editor', `<form method="post" action="/editor${id ? '?id=' + id : ''}"><input name="title" value="${p.title || ''}"><textarea name="body">${p.body || ''}</textarea><select name="status"><option>draft</option><option>published</option></select><button>Save</button></form>`));
    }
    const f = new URLSearchParams(await body(req));
    const id = u.searchParams.get('id');
    if (id) {
      const p = db.prepare('SELECT * FROM posts WHERE id=?').get(id);
      if (!p) return H(404, page('404', 'nope'));
      if (user.id !== p.author_id && user.role !== 'admin') return H(200, page('error', '<p>Forbidden.</p>'));
      db.prepare('UPDATE posts SET title=?, body=?, status=?, updated_at=? WHERE id=?').run(f.get('title'), f.get('body'), f.get('status'), Date.now(), id);
    } else db.prepare('INSERT INTO posts (author_id, title, body, status, created_at, updated_at) VALUES (?,?,?,?,?,?)').run(user.id, f.get('title'), f.get('body'), f.get('status'), Date.now(), Date.now());
    res.writeHead(302, { Location: '/' }); return res.end();
  }
  // JSON API
  if (u.pathname === '/api/v1/posts' && req.method === 'GET') {
    const pg = Math.max(1, parseInt(u.searchParams.get('page') || '1'));
    const rows = db.prepare(`SELECT p.id, p.title, p.status, p.created_at, u.username AS author FROM posts p JOIN users u ON u.id=p.author_id WHERE status='published' ORDER BY created_at DESC LIMIT 10 OFFSET ?`).all((pg - 1) * 10);
    return J(200, { data: rows });
  }
  if (u.pathname === '/api/v1/posts' && req.method === 'POST') {
    if (!user) return J(401, { error: 'unauthorized' });
    if (user.role !== 'author' && user.role !== 'admin') return J(403, { error: 'forbidden' });
    let b; try { b = JSON.parse(await body(req)); } catch { return J(422, { error: 'bad json' }); }
    const r = db.prepare('INSERT INTO posts (author_id, title, body, status, created_at, updated_at) VALUES (?,?,?,?,?,?) RETURNING id').get(user.id, b.title, b.body, b.status || 'draft', Date.now(), Date.now());
    return J(201, { data: r });
  }
  return H(404, page('404', '<h1>Not found</h1>'));
});

server.listen(3001, () => console.log('blog on 3001'));
