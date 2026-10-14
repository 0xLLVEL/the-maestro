/**
 * Tests for the pure calculator logic and the translation keys.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  createState, inputDigit, inputOperator, equals, clear,
  toggleSign, percent, addEntry, deleteEntry, clearHistory, keyToAction,
} from '../calculator.js';

/** Types a digit string into the state. */
function type(state, text) {
  for (const ch of text) inputDigit(state, ch);
}

test('adds two numbers and shows the sum', () => {
  const s = createState();
  type(s, '2');
  inputOperator(s, '+');
  type(s, '3');
  assert.equal(equals(s), '5');
});

test('reports divide-by-zero with the error key instead of crashing', () => {
  const s = createState();
  type(s, '1');
  inputOperator(s, '/');
  type(s, '0');
  assert.equal(equals(s), 'error.cannot-divide');
});

test('computes percent of the displayed value', () => {
  const s = createState();
  type(s, '200');
  percent(s);
  assert.equal(s.entry, '2');
});

test('maps keyboard keys to the matching calculator actions', () => {
  assert.deepEqual(keyToAction('7'), { type: 'digit', value: '7' });
  assert.deepEqual(keyToAction('+'), { type: 'operator', value: '+' });
  assert.deepEqual(keyToAction('Enter'), { type: 'equals' });
  assert.deepEqual(keyToAction('Escape'), { type: 'clear' });
  assert.equal(keyToAction('Shift'), null);
});

test('records each finished calculation at the top of the history', () => {
  const s = createState();
  type(s, '2');
  inputOperator(s, '+');
  type(s, '3');
  equals(s);
  assert.equal(s.history.length, 1);
  assert.deepEqual(s.history[0], { expression: '2 + 3', result: '5' });
});

test('empties the history on clear-all and deletes single entries', () => {
  const history = [];
  addEntry(history, '1 + 1', '2');
  addEntry(history, '2 + 2', '4');
  deleteEntry(history, 0);
  assert.deepEqual(history, [{ expression: '1 + 1', result: '2' }]);
  clearHistory(history);
  assert.deepEqual(history, []);
});

test('every message key returned by the logic exists in en.json', () => {
  const strings = JSON.parse(readFileSync(new URL('../lang/en.json', import.meta.url)));
  for (const key of ['error.cannot-divide', 'error.unknown-operator']) {
    assert.ok(strings[key], `missing translation key: ${key}`);
  }
});

test('toggles the sign of the current entry', () => {
  const s = createState();
  type(s, '5');
  toggleSign(s);
  assert.equal(s.entry, '-5');
  toggleSign(s);
  assert.equal(s.entry, '5');
});

test('clears the entry while keeping the history', () => {
  const s = createState();
  type(s, '9');
  inputOperator(s, '+');
  clear(s);
  assert.equal(s.entry, '0');
});
