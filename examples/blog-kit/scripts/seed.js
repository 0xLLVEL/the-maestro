/**
 * Seeds a demo database with users and posts.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { openDatabase } from '../db.js';
import { createUser } from '../auth.js';
import { createPost } from '../posts.js';

const db = openDatabase(process.env.DB_PATH || 'blog.db');
const admin = createUser(db, 'admin', 'admin-pass-1');
const author = createUser(db, 'ada', 'author-pass-1');
await (async () => {
  const { setUserRole } = await import('../auth.js');
  setUserRole(db, author.id, 'author');
})();
createPost(db, author.id, 'Hello blog', 'First published post.', 'published');
createPost(db, author.id, 'Draft ideas', 'Not ready yet.', 'draft');
console.log(`Seeded admin id=${admin.id}, author id=${author.id}.`);
