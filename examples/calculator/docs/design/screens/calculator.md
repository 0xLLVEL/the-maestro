# Screen: calculator

Static page. Reused components: none (no component library in this project).
New components: display, keypad, history-list. All states below are skeleton blocks:
plain HTML tags, no styling.

## Default (ready)

```html
<main>
  <h1><!-- calculator.title --></h1>
  <section>
    <div><!-- display: current entry and running expression --></div>
    <div>
      <button>C</button><button>+/-</button><button>%</button><button>/</button>
      <button>7</button><button>8</button><button>9</button><button>*</button>
      <button>4</button><button>5</button><button>6</button><button>-</button>
      <button>1</button><button>2</button><button>3</button><button>+</button>
      <button>0</button><button>.</button><button>=</button>
    </div>
  </section>
  <section>
    <h2><!-- history.title --></h2>
    <ul>
      <li><!-- entry: expression = result, delete button --></li>
    </ul>
    <button><!-- history.clear --></button>
  </section>
</main>
```

## Empty history

```html
<main>
  <h1><!-- calculator.title --></h1>
  <section>
    <div><!-- display --></div>
    <div><!-- keypad as above --></div>
  </section>
  <section>
    <h2><!-- history.title --></h2>
    <p><!-- history.empty --></p>
  </section>
</main>
```

## Error (divide by zero)

```html
<main>
  <h1><!-- calculator.title --></h1>
  <section>
    <div><!-- error.cannot-divide message --></div>
    <div><!-- keypad as above --></div>
  </section>
</main>
```
