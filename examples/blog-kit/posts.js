/**
 * Posts: creation, visibility rules, paginated listing, owner-or-admin edits.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */

/** Valid post statuses. */
export const STATUSES = ['draft', 'published'];

/** Maximum posts per page. */
export const MAX_PER_PAGE = 50;

/** Validates a title (1-200 characters). */
export function validTitle(title) {
  return typeof title === 'string' && title.trim().length >= 1 && title.length <= 200;
}

/** Validates a body (1-20000 characters). */
export function validBody(body) {
  return typeof body === 'string' && body.trim().length >= 1 && body.length <= 20000;
}

/** Creates a post for an author; status defaults to draft. */
export function createPost(db, authorId, title, body, status = 'draft') {
  if (!validTitle(title)) throw Object.assign(new Error('Invalid title.'), { code: 422 });
  if (!validBody(body)) throw Object.assign(new Error('Invalid body.'), { code: 422 });
  if (!STATUSES.includes(status)) throw Object.assign(new Error('Unknown status.'), { code: 422 });
  const now = Date.now();
  return db.prepare(
    'INSERT INTO posts (author_id, title, body, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING id, title, status'
  ).get(authorId, title, body, status, now, now);
}

/** Parses pagination input, applying defaults and the per-page cap. */
export function parsePaging(query) {
  const page = Number(query.page ?? 1);
  const perPage = Number(query.per_page ?? 10);
  if (!Number.isInteger(page) || page < 1) throw Object.assign(new Error('Invalid page.'), { code: 422 });
  if (!Number.isInteger(perPage) || perPage < 1 || perPage > MAX_PER_PAGE) {
    throw Object.assign(new Error('Invalid per_page.'), { code: 422 });
  }
  return { page, perPage };
}

/**
 * Lists posts newest first; drafts are included only for author and admin sessions.
 */
export function listPosts(db, user, page, perPage) {
  const privileged = user && (user.role === 'author' || user.role === 'admin');
  const where = privileged ? '' : "WHERE status = 'published'";
  const total = db.prepare(`SELECT COUNT(*) AS n FROM posts ${where}`).get().n;
  const rows = db.prepare(
    `SELECT p.id, p.title, substr(p.body, 1, 200) AS excerpt, p.status, p.created_at, u.username AS author
     FROM posts p JOIN users u ON u.id = p.author_id ${where}
     ORDER BY p.created_at DESC, p.id DESC LIMIT ? OFFSET ?`
  ).all(perPage, (page - 1) * perPage);
  return { posts: rows, page, per_page: perPage, total };
}

/**
 * Reads one post; drafts are visible only to the owner and to admins.
 */
export function getPost(db, user, id) {
  const row = db.prepare(
    'SELECT p.id, p.title, p.body, p.status, p.created_at, p.author_id, u.username AS author FROM posts p JOIN users u ON u.id = p.author_id WHERE p.id = ?'
  ).get(id);
  if (!row) throw Object.assign(new Error('Post not found.'), { code: 404 });
  if (row.status !== 'published' && (!user || (user.id !== row.author_id && user.role !== 'admin'))) {
    throw Object.assign(new Error('Post not found.'), { code: 404 });
  }
  return row;
}

/**
 * Updates title, body, or status; only the owner or an admin may edit.
 */
export function updatePost(db, user, id, patch) {
  const row = db.prepare('SELECT id, author_id FROM posts WHERE id = ?').get(id);
  if (!row) throw Object.assign(new Error('Post not found.'), { code: 404 });
  if (user.id !== row.author_id && user.role !== 'admin') {
    throw Object.assign(new Error('Forbidden.'), { code: 403 });
  }
  const fields = [];
  const values = [];
  if (patch.title !== undefined) {
    if (!validTitle(patch.title)) throw Object.assign(new Error('Invalid title.'), { code: 422 });
    fields.push('title = ?');
    values.push(patch.title);
  }
  if (patch.body !== undefined) {
    if (!validBody(patch.body)) throw Object.assign(new Error('Invalid body.'), { code: 422 });
    fields.push('body = ?');
    values.push(patch.body);
  }
  if (patch.status !== undefined) {
    if (!STATUSES.includes(patch.status)) throw Object.assign(new Error('Unknown status.'), { code: 422 });
    fields.push('status = ?');
    values.push(patch.status);
  }
  if (fields.length === 0) throw Object.assign(new Error('Nothing to update.'), { code: 422 });
  fields.push('updated_at = ?');
  values.push(Date.now(), id);
  db.prepare(`UPDATE posts SET ${fields.join(', ')} WHERE id = ?`).run(...values);
  return getPost(db, user, id);
}

/**
 * Deletes a post; only the owner or an admin may delete.
 */
export function deletePost(db, user, id) {
  const row = db.prepare('SELECT id, author_id FROM posts WHERE id = ?').get(id);
  if (!row) throw Object.assign(new Error('Post not found.'), { code: 404 });
  if (user.id !== row.author_id && user.role !== 'admin') {
    throw Object.assign(new Error('Forbidden.'), { code: 403 });
  }
  db.prepare('DELETE FROM posts WHERE id = ?').run(id);
}
