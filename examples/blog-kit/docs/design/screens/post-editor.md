# Screen: post-editor

Create and edit form for authors. Reused components: none. New: editor-form.
Skeleton, plain tags, no styling.

## Default

```html
<main>
  <h1><!-- new post / edit post --></h1>
  <section>
    <form>
      <label><!-- title --><input name="title"></label>
      <label><!-- body --><textarea name="body"></textarea></label>
      <label><!-- status --><select name="status"></select></label>
      <button><!-- save --></button>
    </form>
  </section>
</main>
```

## Error (validation)

```html
<main>
  <h1><!-- new post / edit post --></h1>
  <section>
    <ul><!-- one item per invalid field --></ul>
    <form><!-- same fields, values kept --></form>
  </section>
</main>
```
