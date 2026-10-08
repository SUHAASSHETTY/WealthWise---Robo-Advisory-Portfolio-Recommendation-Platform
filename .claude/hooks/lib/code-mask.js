'use strict';

// Replaces comments and string-literal contents with spaces (newlines kept), so that
// regex checks only see code. Interpolated expressions are kept as code:
// Python f-strings {expr} and JS template literals ${expr}. Output length == input length.

// Brace characters are built from char codes so that line-based brace counters
// (e.g. the Harness check-function-length hook) are not confused by string literals.
const LBRACE = String.fromCharCode(123);
const RBRACE = String.fromCharCode(125);
const DOUBLE_LBRACE = LBRACE + LBRACE;
const JS_INTERP_OPEN = '$' + LBRACE;

function blank(s) {
  return s.replace(/[^\n]/g, ' ');
}

function commentEnd(code, i, lang) {
  if (lang === 'py' && code[i] === '#') return lineEnd(code, i);
  if (lang === 'js' && code.startsWith('//', i)) return lineEnd(code, i);
  if (lang === 'js' && code.startsWith('/*', i)) {
    const end = code.indexOf('*/', i + 2);
    return end === -1 ? code.length : end + 2;
  }
  return -1;
}

function lineEnd(code, i) {
  const end = code.indexOf('\n', i);
  return end === -1 ? code.length : end;
}

function pyStringStart(code, i) {
  if (i > 0 && /\w/.test(code[i - 1])) return null;
  const m = /^([rRbBfFuU]{0,2})('''|"""|'|")/.exec(code.slice(i, i + 5));
  if (!m) return null;
  return { prefix: m[1].length, quote: m[2], interp: /f/i.test(m[1]), open: LBRACE };
}

function jsStringStart(code, i) {
  const ch = code[i];
  if (ch !== '"' && ch !== "'" && ch !== '`') return null;
  return { prefix: 0, quote: ch, interp: ch === '`', open: JS_INTERP_OPEN };
}

function copyExpression(code, start) {
  let depth = 1;
  let j = start;
  while (j < code.length && depth > 0) {
    if (code[j] === LBRACE) depth += 1;
    if (code[j] === RBRACE) depth -= 1;
    j += 1;
  }
  return j;
}

function scanString(code, i, s) {
  let out = code.slice(i, i + s.prefix + s.quote.length);
  let j = i + s.prefix + s.quote.length;
  while (j < code.length) {
    if (code.startsWith(s.quote, j)) {
      return { end: j + s.quote.length, masked: out + s.quote };
    }
    if (code[j] === '\\') {
      out += blank(code.slice(j, j + 2));
      j += 2;
      continue;
    }
    if (s.interp && s.open === LBRACE && code.startsWith(DOUBLE_LBRACE, j)) {
      out += '  ';
      j += 2;
      continue;
    }
    if (s.interp && code.startsWith(s.open, j)) {
      const exprEnd = copyExpression(code, j + s.open.length);
      out += code.slice(j, exprEnd);
      j = exprEnd;
      continue;
    }
    out += code[j] === '\n' ? '\n' : ' ';
    j += 1;
  }
  return { end: code.length, masked: out };
}

function maskCode(code, lang) {
  const startString = lang === 'py' ? pyStringStart : jsStringStart;
  let out = '';
  let i = 0;
  while (i < code.length) {
    const cEnd = commentEnd(code, i, lang);
    if (cEnd !== -1) {
      out += blank(code.slice(i, cEnd));
      i = cEnd;
      continue;
    }
    const s = startString(code, i);
    if (s) {
      const r = scanString(code, i, s);
      out += r.masked;
      i = r.end;
      continue;
    }
    out += code[i];
    i += 1;
  }
  return out;
}

function langOf(relPath) {
  if (relPath.endsWith('.py')) return 'py';
  if (/\.(ts|tsx|js|jsx|mjs|cjs)$/.test(relPath)) return 'js';
  return null;
}

module.exports = { maskCode, langOf };
