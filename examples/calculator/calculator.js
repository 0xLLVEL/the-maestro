/**
 * Pure calculator logic: arithmetic, entry editing, and history.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */

/** Creates a fresh calculator state object. */
export function createState() {
  return { entry: '0', operand: null, operator: null, fresh: true, history: [] };
}

/** Maximum significant digits shown on the display. */
const MAX_DIGITS = 12;

/**
 * Formats a numeric result for the display, rounding beyond the digit limit.
 */
export function formatResult(value) {
  if (!Number.isFinite(value)) return { ok: false, key: 'error.cannot-divide' };
  const rounded = Number(value.toPrecision(MAX_DIGITS));
  return { ok: true, text: String(rounded) };
}

/**
 * Evaluates one binary operation, returning either the formatted text or an error key.
 */
export function evaluate(left, operator, right) {
  const a = Number(left);
  const b = Number(right);
  switch (operator) {
    case '+': return formatResult(a + b);
    case '-': return formatResult(a - b);
    case '*': return formatResult(a * b);
    case '/': return b === 0 ? { ok: false, key: 'error.cannot-divide' } : formatResult(a / b);
    default: return { ok: false, key: 'error.unknown-operator' };
  }
}

/** Appends a digit or a single decimal dot to the current entry. */
export function inputDigit(state, ch) {
  if (state.fresh) {
    state.entry = ch === '.' ? '0.' : ch;
    state.fresh = false;
    return;
  }
  if (ch === '.' && state.entry.includes('.')) return;
  if (state.entry.replace(/[-.]/g, '').length >= MAX_DIGITS) return;
  state.entry = (state.entry === '0' && ch !== '.') ? ch : state.entry + ch;
}

/** Stores the pending operation, chaining through any earlier one first. */
export function inputOperator(state, operator) {
  if (state.operator !== null && !state.fresh) equals(state);
  state.operand = state.entry;
  state.operator = operator;
  state.fresh = true;
}

/**
 * Completes the pending operation, records history, and shows the result or an error key.
 */
export function equals(state) {
  if (state.operator === null || state.operand === null) return state.entry;
  const expression = `${state.operand} ${state.operator} ${state.entry}`;
  const out = evaluate(state.operand, state.operator, state.entry);
  if (!out.ok) {
    state.entry = out.key;
  } else {
    state.entry = out.text;
    addEntry(state.history, expression, out.text);
  }
  state.operand = null;
  state.operator = null;
  state.fresh = true;
  return state.entry;
}

/** Resets the entry and any pending operation, keeping the history. */
export function clear(state) {
  state.entry = '0';
  state.operand = null;
  state.operator = null;
  state.fresh = true;
}

/** Negates the sign of the current entry. */
export function toggleSign(state) {
  state.entry = state.entry.startsWith('-') ? state.entry.slice(1) : '-' + state.entry;
  state.fresh = false;
}

/** Divides the current entry by one hundred (percent). */
export function percent(state) {
  const out = formatResult(Number(state.entry) / 100);
  state.entry = out.ok ? out.text : out.key;
  state.fresh = true;
}

/** Prepends a calculation entry to the history list. */
export function addEntry(history, expression, result) {
  history.unshift({ expression, result });
}

/** Removes the history entry at the given index. */
export function deleteEntry(history, index) {
  history.splice(index, 1);
}

/** Removes every history entry. */
export function clearHistory(history) {
  history.length = 0;
}

/**
 * Maps a physical keyboard key to a calculator action descriptor.
 */
export function keyToAction(key) {
  if (/^[0-9.]$/.test(key)) return { type: 'digit', value: key };
  if (['+', '-', '*', '/'].includes(key)) return { type: 'operator', value: key };
  if (key === 'Enter' || key === '=') return { type: 'equals' };
  if (key === 'Escape') return { type: 'clear' };
  if (key === '%') return { type: 'percent' };
  return null;
}
