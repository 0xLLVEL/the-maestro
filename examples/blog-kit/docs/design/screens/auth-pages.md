# Screen: auth-pages

Register, login, and logout forms. Reused components: none. New: auth-form.
Skeleton, plain tags, no styling.

## Default

```html
<main>
  <h1><!-- blog.login --></h1>
  <section>
    <form>
      <label><!-- username --><input name="username"></label>
      <label><!-- password --><input name="password" type="password"></label>
      <button><!-- blog.login --></button>
    </form>
    <p><!-- link to register --></p>
  </section>
</main>
```

## Error (invalid credentials)

```html
<main>
  <h1><!-- blog.login --></h1>
  <section>
    <p><!-- auth.invalid --></p>
    <form><!-- same fields as above --></form>
  </section>
</main>
```
