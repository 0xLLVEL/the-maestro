# Screen: post-list

Public paginated list of published posts. Reused components: none. New: post-card, pager.
Skeleton, plain tags, no styling.

## Default

```html
<main>
  <h1><!-- blog.title --></h1>
  <section>
    <article>
      <h2><!-- post title, link to detail --></h2>
      <p><!-- author and date --></p>
    </article>
    <nav><!-- pager: prev, page numbers, next --></nav>
  </section>
</main>
```

## Empty (no posts)

```html
<main>
  <h1><!-- blog.title --></h1>
  <section>
    <p><!-- posts.empty --></p>
  </section>
</main>
```
