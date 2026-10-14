/**
 * HTML views: escaping and page templates for the four screens.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */

/** Escapes text for safe HTML output. */
export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

/** Wraps body content in the site layout with linked stylesheet. */
export function layout(title, body) {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>${escapeHtml(title)}</title><link rel="stylesheet" href="/styles.css"></head>
<body><main>${body}</main></body>
</html>`;
}

/** Renders the login and register forms with an optional error message. */
export function authPage(mode, error = '') {
  const other = mode === 'login' ? 'register' : 'login';
  return layout(mode === 'login' ? 'Login' : 'Register', `
    <h1>${mode === 'login' ? 'Login' : 'Register'}</h1>
    <section>
      ${error ? `<p>${escapeHtml(error)}</p>` : ''}
      <form method="post" action="/${mode}">
        <label>Username<input name="username"></label>
        <label>Password<input name="password" type="password"></label>
        <button>${mode === 'login' ? 'Login' : 'Register'}</button>
      </form>
      <p><a href="/${other}">${other}</a></p>
    </section>`);
}

/** Renders the paginated published list with page links. */
export function listPage(result, strings) {
  const cards = result.posts.map((p) => `
    <article>
      <h2><a href="/posts/${p.id}">${escapeHtml(p.title)}</a></h2>
      <p>${escapeHtml(p.author)}</p>
    </article>`).join('');
  const pages = Math.max(1, Math.ceil(result.total / result.per_page));
  let links = '';
  for (let n = 1; n <= pages; n += 1) {
    links += n === result.page ? `<span>${n}</span>` : `<a href="/?page=${n}">${n}</a>`;
  }
  const body = result.posts.length === 0
    ? `<p>${escapeHtml(strings['posts.empty'])}</p>`
    : `${cards}<nav>${links}</nav>`;
  return layout(strings['blog.title'], `<h1>${escapeHtml(strings['blog.title'])}</h1><section>${body}</section>`);
}

/** Renders a single post with author and date. */
export function detailPage(post) {
  return layout(post.title, `
    <article>
      <h1>${escapeHtml(post.title)}</h1>
      <p>${escapeHtml(post.author)}</p>
      <div>${escapeHtml(post.body)}</div>
    </article>`);
}

/** Renders the create and edit form, keeping submitted values on error. */
export function editorPage(post = { title: '', body: '', status: 'draft' }, errors = []) {
  const items = errors.map((e) => `<li>${escapeHtml(e)}</li>`).join('');
  return layout('Editor', `
    <h1>Editor</h1>
    <section>
      ${items ? `<ul>${items}</ul>` : ''}
      <form method="post" action="/editor${post.id ? `?id=${post.id}` : ''}">
        <label>Title<input name="title" value="${escapeHtml(post.title)}"></label>
        <label>Body<textarea name="body">${escapeHtml(post.body)}</textarea></label>
        <label>Status<select name="status">
          <option value="draft"${post.status === 'draft' ? ' selected' : ''}>draft</option>
          <option value="published"${post.status === 'published' ? ' selected' : ''}>published</option>
        </select></label>
        <button>Save</button>
      </form>
    </section>`);
}
