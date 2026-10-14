/**
 * Binds the calculator logic to the skeleton DOM: display, keypad, history, keyboard.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import {
  createState, inputDigit, inputOperator, equals, clear,
  toggleSign, percent, deleteEntry, clearHistory, keyToAction,
} from './calculator.js';

const state = createState();
let strings = {};

/** Resolves a logic message key through the translation file. */
function text(value) {
  return strings[value] || value;
}

/** Renders the display, history list, and translated labels. */
function render() {
  document.getElementById('display').textContent = text(state.entry);
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = text(el.getAttribute('data-i18n'));
  });
  const list = document.getElementById('history');
  list.replaceChildren();
  state.history.forEach((item, index) => {
    const row = document.createElement('li');
    row.textContent = `${item.expression} = ${item.result} `;
    const del = document.createElement('button');
    del.textContent = text('history.delete');
    del.addEventListener('click', () => {
      deleteEntry(state.history, index);
      render();
    });
    row.appendChild(del);
    list.appendChild(row);
  });
  document.getElementById('history-empty').hidden = state.history.length > 0;
}

/** Applies one calculator action descriptor, then re-renders. */
function apply(action) {
  if (action === null) return;
  switch (action.type) {
    case 'digit': inputDigit(state, action.value); break;
    case 'operator': inputOperator(state, action.value); break;
    case 'equals': equals(state); break;
    case 'clear': clear(state); break;
    case 'percent': percent(state); break;
    case 'sign': toggleSign(state); break;
    default: return;
  }
  render();
}

document.getElementById('keypad').addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button) return;
  const { action } = button.dataset;
  if (action === 'digit' || action === 'operator') {
    apply({ type: action, value: button.dataset.value });
  } else {
    apply({ type: action });
  }
});

document.getElementById('history-clear').addEventListener('click', () => {
  clearHistory(state.history);
  render();
});

document.addEventListener('keydown', (event) => {
  if (event.key === ' ' || event.key === 'Tab') return;
  const before = state.entry;
  apply(keyToAction(event.key));
  if (state.entry !== before || event.key === 'Enter') event.preventDefault();
});

fetch('lang/en.json')
  .then((response) => response.json())
  .then((data) => { strings = data; render(); });
